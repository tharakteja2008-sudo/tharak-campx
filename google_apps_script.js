// ============================================================
// Google Apps Script: CampX Daily Attendance Reporter (SVCE Tirupati)
// Compatible with all Google Apps Script runtimes (100% pure JS)
// ============================================================

var CAMPX_BASE_URL = "https://svce.campx.in";
var CAMPX_API_URL = "https://api.campx.in";
var CAMPX_USERNAME = "25BFA32091";
var CAMPX_PASSWORD = "25BFA32091";
var CAMPX_TENANT = "svce";
var CAMPX_INSTITUTION = "svce";
var RECIPIENT_EMAIL = "tharakteja2008@gmail.com";

var CLIENT_ID = "efa4ddab-3031-4370-ad77-46557d4f0890";
var CLIENT_SECRET = "9KubLTSkNJMStC+Q3MhXUHPCfgbkkEb4ssyib0jfaMs=";

function base64UrlEncode(str) {
  return Utilities.base64EncodeWebSafe(str).replace(/=+$/, "");
}

function generateCampxClientToken() {
  var payload = JSON.stringify({
    clientId: CLIENT_ID,
    iat: Math.floor(new Date().getTime() / 1000)
  });
  var r = base64UrlEncode(payload);
  var signatureBytes = Utilities.computeHmacSha256Signature(r, CLIENT_SECRET);
  var signature = Utilities.base64EncodeWebSafe(signatureBytes).replace(/=+$/, "");
  return r + "." + signature;
}

function sendDailyCampXAttendance() {
  var clientToken = generateCampxClientToken();

  // 1. Login to CampX
  var loginPayload = {
    username: CAMPX_USERNAME,
    password: CAMPX_PASSWORD,
    loginId: CAMPX_USERNAME,
    loginType: "USER",
    deviceType: "browser",
    clientName: "Chrome",
    os: "Windows",
    osVersion: "10",
    latitude: 13.6288,
    longitude: 79.4192,
    tokenType: "WEB"
  };

  var loginOptions = {
    method: "post",
    contentType: "application/json",
    headers: {
      "User-Agent": "Mozilla/5.0",
      "Origin": CAMPX_BASE_URL,
      "Referer": CAMPX_BASE_URL + "/auth/login",
      "x-tenant-id": CAMPX_TENANT,
      "x-institution-code": "auth",
      "x-platform-id": "campx",
      "x-campx-client": clientToken
    },
    payload: JSON.stringify(loginPayload),
    muteHttpExceptions: true
  };

  var loginResp = UrlFetchApp.fetch(CAMPX_API_URL + "/auth-server/auth-v2/login", loginOptions);
  var loginStatus = loginResp.getResponseCode();
  if (loginStatus !== 200 && loginStatus !== 201) {
    Logger.log("Login failed: " + loginResp.getContentText());
    return;
  }

  // Extract cookies
  var headers = loginResp.getAllHeaders();
  var cookieHeader = "";
  if (headers["Set-Cookie"]) {
    var rawCookies = [];
    if (Array.isArray(headers["Set-Cookie"])) {
      rawCookies = headers["Set-Cookie"];
    } else {
      rawCookies = [headers["Set-Cookie"]];
    }
    var cookieParts = [];
    for (var i = 0; i < rawCookies.length; i++) {
      cookieParts.push(rawCookies[i].split(";")[0]);
    }
    cookieHeader = cookieParts.join("; ");
  }

  // 2. Fetch Attendance
  var attendanceOptions = {
    method: "get",
    headers: {
      "User-Agent": "Mozilla/5.0",
      "Origin": CAMPX_BASE_URL,
      "Referer": CAMPX_BASE_URL + "/" + CAMPX_INSTITUTION + "/student-workspace",
      "x-tenant-id": CAMPX_TENANT,
      "x-institution-code": CAMPX_INSTITUTION,
      "x-platform-id": "campx",
      "x-campx-client": generateCampxClientToken(),
      "Cookie": cookieHeader
    },
    muteHttpExceptions: true
  };

  var attResp = UrlFetchApp.fetch(CAMPX_API_URL + "/student-api/student-attendance", attendanceOptions);
  if (attResp.getResponseCode() !== 200) {
    Logger.log("Attendance fetch failed: " + attResp.getContentText());
    return;
  }

  var rawSubjects = JSON.parse(attResp.getContentText());

  // 3. Process Attendance & Calculate Delta
  var props = PropertiesService.getScriptProperties();
  var prevHistoryRaw = props.getProperty("campx_history");
  var prevHistory = null;
  if (prevHistoryRaw) {
    try {
      prevHistory = JSON.parse(prevHistoryRaw);
    } catch (e) {
      prevHistory = null;
    }
  }

  var totalConducted = 0;
  var totalAttended = 0;
  var subjects = [];
  var prevSubjectsMap = {};

  if (prevHistory && prevHistory.subjects) {
    for (var j = 0; j < prevHistory.subjects.length; j++) {
      var item = prevHistory.subjects[j];
      prevSubjectsMap[item.subjectId] = item;
    }
  }

  var todayAttended = [];
  var todayMissed = [];

  for (var k = 0; k < rawSubjects.length; k++) {
    var s = rawSubjects[k];
    var sid = s.subjectId;
    var name = s.subjectName || "Subject";
    var code = s.refCode || "";
    var conducted = parseInt(s.numberOfClasses || 0, 10);
    var present = parseInt(s.present || 0, 10);
    var absent = parseInt(s.absent || 0, 10);
    var pct = parseFloat(s.percentage || 0);

    totalConducted += conducted;
    totalAttended += present;

    if (prevSubjectsMap[sid]) {
      var prev = prevSubjectsMap[sid];
      var newPresent = present - (prev.attended || present);
      var newAbsent = absent - (prev.absent || absent);
      if (newPresent > 0) {
        todayAttended.push(name + " (" + code + ") — " + newPresent + " class(es)");
      }
      if (newAbsent > 0) {
        todayMissed.push(name + " (" + code + ") — " + newAbsent + " class(es)");
      }
    }

    subjects.push({
      subjectId: sid,
      name: name,
      refCode: code,
      conducted: conducted,
      attended: present,
      absent: absent,
      percentage: pct
    });
  }

  var overallPct = totalConducted > 0 ? ((totalAttended / totalConducted) * 100).toFixed(2) : "0.00";
  var prevOverall = prevHistory ? prevHistory.overall_percentage : overallPct;
  var diffVal = (parseFloat(overallPct) - parseFloat(prevOverall)).toFixed(2);

  var deltaStr = "No change (0.00%)";
  if (!prevHistory) {
    deltaStr = "Initial Cloud Report";
  } else if (parseFloat(diffVal) > 0) {
    deltaStr = "Increased by +" + diffVal + "%";
  } else if (parseFloat(diffVal) < 0) {
    deltaStr = "Decreased by " + diffVal + "%";
  }

  // 4. Bunk / Margin
  var marginInfo = "";
  if (parseFloat(overallPct) >= 75) {
    var safeBunks = Math.floor((totalAttended * 100 / 75) - totalConducted);
    if (safeBunks > 0) {
      marginInfo = "<b>Safe Zone:</b> You can miss <b>" + safeBunks + " class(es)</b> and still maintain above 75%.";
    } else {
      marginInfo = "<b>Borderline:</b> You are at " + overallPct + "%. Avoid missing classes.";
    }
  } else {
    var req = Math.ceil(((0.75 * totalConducted) - totalAttended) / 0.25);
    marginInfo = "<b>Warning:</b> You need to attend <b>" + req + " consecutive classes</b> to reach 75%.";
  }

  // 5. Generate Email HTML
  var badgeColor = parseFloat(overallPct) >= 75 ? "#10b981" : "#ef4444";
  var deltaColor = parseFloat(diffVal) > 0 ? "#10b981" : (parseFloat(diffVal) < 0 ? "#ef4444" : "#64748b");

  var missedHtml = "";
  if (todayMissed.length > 0) {
    var mList = "";
    for (var m = 0; m < todayMissed.length; m++) {
      mList += "<li>[ABSENT] <b>" + todayMissed[m] + "</b></li>";
    }
    missedHtml = "<div style='background:#fef2f2; border-left:4px solid #ef4444; padding:12px; border-radius:8px; margin:15px 0;'>" +
                 "<h4 style='margin:0 0 6px 0; color:#991b1b;'>Classes Missed Today:</h4>" +
                 "<ul style='margin:0; padding-left:20px; color:#dc2626;'>" + mList + "</ul></div>";
  } else {
    missedHtml = "<div style='background:#f0fdf4; border-left:4px solid #10b981; padding:10px; border-radius:8px; margin:15px 0; color:#166534;'>" +
                 "<b>Great job!</b> No classes were missed today.</div>";
  }

  var attendedHtml = "";
  if (todayAttended.length > 0) {
    var aList = "";
    for (var a = 0; a < todayAttended.length; a++) {
      aList += "<li>[ATTENDED] " + todayAttended[a] + "</li>";
    }
    attendedHtml = "<div style='background:#f0fdf4; border-left:4px solid #10b981; padding:12px; border-radius:8px; margin:15px 0;'>" +
                   "<h4 style='margin:0 0 6px 0; color:#166534;'>Classes Attended Today:</h4>" +
                   "<ul style='margin:0; padding-left:20px; color:#16a34a;'>" + aList + "</ul></div>";
  }

  var subjectRows = "";
  for (var sIdx = 0; sIdx < subjects.length; sIdx++) {
    var sub = subjects[sIdx];
    var subColor = sub.percentage >= 75 ? "#10b981" : "#ef4444";
    subjectRows += "<tr style='border-bottom:1px solid #f1f5f9;'>" +
                   "<td style='padding:10px 8px;'><b>" + sub.name + "</b><br><span style='font-size:11px;color:#64748b;'>" + sub.refCode + "</span></td>" +
                   "<td style='padding:10px 8px; text-align:center;'>" + sub.attended + "/" + sub.conducted + "</td>" +
                   "<td style='padding:10px 8px; text-align:right; color:" + subColor + "; font-weight:bold;'>" + sub.percentage.toFixed(2) + "%</td>" +
                   "</tr>";
  }

  var dateStr = Utilities.formatDate(new Date(), "Asia/Kolkata", "dd MMMM yyyy");
  var emailHtml = "<div style='font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif; max-width:600px; margin:0 auto; background:#fff; border-radius:14px; overflow:hidden; border:1px solid #e2e8f0;'>" +
    "<div style='background:linear-gradient(135deg,#1e3a8a,#2563eb); color:#fff; padding:22px; text-align:center;'>" +
      "<h2 style='margin:0; font-size:20px;'>Sri Venkateswara College of Engineering</h2>" +
      "<p style='margin:5px 0 0; opacity:0.9; font-size:13px;'>CampX Daily Attendance Alert &bull; " + dateStr + "</p>" +
      "<p style='margin:8px 0 0; font-size:12px; background:rgba(255,255,255,0.2); display:inline-block; padding:3px 12px; border-radius:12px;'>P THARAK TEJA (25BFA32091) &bull; CSE(CSD)</p>" +
    "</div>" +
    "<div style='padding:22px; color:#334155;'>" +
      "<div style='background:#f8fafc; border:1px solid #e2e8f0; border-radius:12px; padding:18px; text-align:center;'>" +
        "<div style='font-size:11px; text-transform:uppercase; letter-spacing:1px; color:#64748b; font-weight:700;'>Overall Attendance</div>" +
        "<div style='font-size:42px; font-weight:900; color:" + badgeColor + "; margin:6px 0;'>" + overallPct + "%</div>" +
        "<div style='display:inline-block; padding:3px 12px; border-radius:20px; font-size:13px; font-weight:700; color:" + deltaColor + "; background:#fff; border:1px solid #e2e8f0;'>" + deltaStr + "</div>" +
        "<div style='font-size:13px; color:#64748b; margin-top:8px;'>Classes Attended: <b>" + totalAttended + "</b> / <b>" + totalConducted + "</b></div>" +
      "</div>" +
      missedHtml +
      attendedHtml +
      "<div style='background:#f8fafc; border:1px dashed #cbd5e1; padding:12px; border-radius:8px; margin:16px 0; font-size:13px;'>" +
        marginInfo +
      "</div>" +
      "<h4 style='margin:20px 0 8px;'>Subject-wise Attendance:</h4>" +
      "<table style='width:100%; border-collapse:collapse; font-size:13px;'>" +
        "<thead><tr style='background:#f1f5f9; color:#475569; text-align:left;'><th style='padding:8px;'>Subject</th><th style='padding:8px;text-align:center;'>Attended</th><th style='padding:8px;text-align:right;'>%</th></tr></thead>" +
        "<tbody>" + subjectRows + "</tbody>" +
      "</table>" +
    "</div>" +
    "<div style='background:#f8fafc; padding:14px; text-align:center; font-size:12px; color:#94a3b8; border-top:1px solid #e2e8f0;'>" +
      "Cloud Automated &bull; SVCE Tirupati &bull; Sent to " + RECIPIENT_EMAIL +
    "</div>" +
  "</div>";

  var shortDate = Utilities.formatDate(new Date(), "Asia/Kolkata", "dd MMM");
  var emailSubject = "CampX Attendance: " + overallPct + "% | SVCE Tirupati (" + shortDate + ")";

  GmailApp.sendEmail(RECIPIENT_EMAIL, emailSubject, "", {
    htmlBody: emailHtml,
    name: "SVCE CampX Tracker"
  });

  props.setProperty("campx_history", JSON.stringify({
    overall_percentage: overallPct,
    total_conducted: totalConducted,
    total_attended: totalAttended,
    subjects: subjects
  }));

  Logger.log("Attendance email sent successfully!");
}
