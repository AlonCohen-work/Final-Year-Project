const express = require("express");
const mongojs = require("mongojs");
const cors = require("cors");
const { exec } = require('child_process');
const path = require('path');

const app = express();
app.use(express.json());
app.use(cors());

// MongoDB Atlas connection
const dbURI = "mongodb+srv://alon123179:23892389Aa@cluster0.arcpa.mongodb.net/people?retryWrites=true&w=majority";
const db = mongojs(dbURI);
const people_coll = db.collection("people");
const Workplace_coll = db.collection("Workplace");
const result_coll = db.collection("result");
const announcements_coll = db.collection("announcements");

db.on("connect", () => {
  console.log("✅ Connected to MongoDB Atlas");
});

db.on("error", (err) => {
  console.error("❌ Database connection error:", err);
});

// Login endpoint
app.post("/login", (req, res) => {
  const { id, password } = req.body;

  const numericId = parseInt(id);
  if (isNaN(numericId)) {
    return res.status(400).json({ success: false, message: "Invalid ID format" });
  }

  people_coll.findOne({ _id: numericId }, (err, user) => {
    if (err) {
      console.error("❌ Database error on login:", err);
      return res.status(500).json({ success: false, message: "Database error" });
    }

    if (user && user.password === password) {
      Workplace_coll.findOne(
        { hotelName: user.Workplace },
        (hotelErr, hotelData) => {
          if (hotelErr) {
            console.error("❌ Error retrieving workplace data on login:", hotelErr);
            return res.status(500).json({ success: false, message: "Error retrieving workplace data" });
          }

          res.json({
            success: true,
            id: user._id,
            name: user.name,
            job: user.job,
            Workplace: user.Workplace,
            ShiftManager: user.ShiftManager,
            WeaponCertified: user.WeaponCertified,
            selectedDays: user.selectedDays || [],
            schedule: hotelData && hotelData.schedule ? hotelData.schedule : {},
          });
        }
      );
    } else {
      console.log(`❌ Login failed for user: ${id}`);
      res.status(401).json({ success: false, message: "Invalid ID or password" });
    }
  });
});

// EmployeeRequest endpoints
app.post("/EmployeeRequest", (req, res) => {
  const { userId, selectedDays } = req.body;

  if (!userId || !Array.isArray(selectedDays)) {
    return res.status(400).json({ success: false, message: "Invalid data format" });
  }

  const numericId = parseInt(userId, 10);
  if (isNaN(numericId)) {
    return res.status(400).json({ success: false, message: "Invalid userId format" });
  }

  people_coll.updateOne(
    { _id: numericId },
    { $set: { selectedDays: selectedDays, availabilityLastUpdated: new Date() } },
    (updateErr) => {
      if (updateErr) {
        console.error("Error during update:", updateErr);
        return res.status(500).json({ success: false, message: "Error updating data" });
      }
      res.status(200).json({ success: true, message: "Days updated successfully" });
    }
  );
});

app.get("/EmployeeRequest", (req, res) => {
  const userId = parseInt(req.query.userId);
  if (isNaN(userId)) {
    return res.status(400).json({ success: false, message: "Invalid userId format" });
  }

  people_coll.findOne({ _id: userId }, (err, user) => {
    if (err) {
      console.error("❌ Error fetching user:", err);
      return res.status(500).json({ success: false, message: "Database error" });
    }

    if (!user) {
      return res.status(404).json({ success: false, message: "User not found" });
    }

    res.json({ success: true, selectedDays: user.selectedDays || [] });
  });
});

// Schedule management endpoints
app.get("/get-schedule/:hotelName", (req, res) => {
  const hotelName = req.params.hotelName;
  Workplace_coll.findOne({ hotelName: hotelName }, (err, data) => {
    if (err) {
      console.error(`DB error fetching schedule for ${hotelName}:`, err);
      return res.status(500).json({ message: "Database error", schedule: {} });
    }
    if (!data) {
      console.log(`No workplace found for ${hotelName}, sending empty schedule object.`);
      return res.status(404).json({ message: "Workplace not found", schedule: {} });
    }
    res.json({ schedule: data.schedule || {} });
  });
});

app.post("/save-schedule/:hotelName", (req, res) => {
  const hotelNameFromParam = req.params.hotelName; // שיניתי את שם המשתנה כדי שיהיה ברור שהוא מה-URL
  const { schedule } = req.body;

  if (!schedule || typeof schedule !== 'object') {
    return res.status(400).json({ success: false, message: "Schedule data is missing or invalid." });
  }

  console.log(`Attempting to find workplace in Workplace_coll: "${hotelNameFromParam}"`);
  Workplace_coll.findOne({ hotelName: hotelNameFromParam }, (findErr, foundDoc) => {
    if (findErr) {
      console.error(`Database error while trying to find workplace "${hotelNameFromParam}":`, findErr);
      return res.status(500).json({ success: false, message: "Error checking if workplace exists." });
    }
    if (foundDoc) {
      console.log(`Workplace "${hotelNameFromParam}" FOUND by findOne. Document:`, JSON.stringify(foundDoc, null, 2));
    } else {
      console.log(`Workplace "${hotelNameFromParam}" WAS NOT FOUND by findOne.`);
    }
    console.log(`Now attempting to updateOne for workplace: "${hotelNameFromParam}"`);

    Workplace_coll.updateOne(
      { hotelName: hotelNameFromParam }, // התנאי לחיפוש
      { $set: { schedule: schedule } },    // הנתונים לעדכון
      { upsert: true },                    // אפשר יצירה אם לא קיים
      (updateErr, result) => {
        if (updateErr) {
          console.error(`Database error during updateOne for "${hotelNameFromParam}":`, updateErr);
          return res.status(500).json({ success: false, message: "Error saving schedule data during update." });
        }
        
        // הדפסת התוצאה הגולמית מ-mongojs
        console.log(`Raw update result from mongojs for "${hotelNameFromParam}":`, JSON.stringify(result, null, 2));
        let operationSucceeded = false;
        let successMessage = "";

        if (result && (result.ok === 1 || result.acknowledged === true)) { // acknowledged נוסף ליתר ביטחון
            if (result.upserted && result.upserted.length > 0) {
                operationSucceeded = true;
                successMessage = `New schedule created successfully for "${hotelNameFromParam}".`;
                console.log(successMessage + ` Upserted ID: ${result.upserted[0]._id}`);
            } else if (result.nModified > 0) {
                operationSucceeded = true;
                successMessage = `Schedule updated successfully for "${hotelNameFromParam}".`;
                console.log(successMessage + ` Matched: ${result.n}, Modified: ${result.nModified}`);
            } else if (result.n > 0 && result.nModified === 0) {
                // נמצאה רשומה, אבל לא בוצע שינוי (כי הנתונים זהים)
                operationSucceeded = true; // עדיין נחשיב כהצלחה מבחינת מציאת הרשומה
                successMessage = `Schedule for "${hotelNameFromParam}" found, but no changes were needed.`;
                console.log(successMessage + ` Matched: ${result.n}`);
            } else if (result.n === 0 && (!result.upserted || result.upserted.length === 0)) {
                // לא נמצא, וגם לא בוצע upsert - זה המקרה של 404
                console.log(`updateOne for "${hotelNameFromParam}": No document matched and no document was upserted.`);
            } else {
                 // מקרה לא צפוי אחר שלכאורה ok:1 אבל לא ברור מה קרה
                 console.log(`updateOne for "${hotelNameFromParam}": ok:1 but unclear outcome. n=${result.n}, nModified=${result.nModified}, upserted=${JSON.stringify(result.upserted)}`);
            }
        } else {
            console.log(`updateOne for "${hotelNameFromParam}": Operation not acknowledged or 'ok' not 1. Result:`, JSON.stringify(result, null, 2));
        }

        if (operationSucceeded) {
          res.status(200).json({ success: true, message: successMessage });
        } else {
          // אם לא הייתה הצלחה מובהקת (כולל המקרה של n=0 ואין upsert)
          console.log(` النهائية: Workplace not found or no changes applied for "${hotelNameFromParam}". Full result object was printed above.`);
          return res.status(404).json({ success: false, message: `Workplace "${hotelNameFromParam}" not found or no changes applied.` });
        }
      }
    );
  });
});
// ...

// Scheduler endpoints
app.post("/api/run-scheduler/:hotelName", (req, res) => {
  const hotelName = req.params.hotelName;
  const { targetWeekStartDate } = req.body;

  if (!targetWeekStartDate) {
    return res.status(400).json({ success: false, message: "Target week start date is required." });
  }
  if (!/^\d{4}-\d{2}-\d{2}$/.test(targetWeekStartDate)) {
    return res.status(400).json({ success: false, message: "Invalid targetWeekStartDate format. Expected YYYY-MM-DD." });
  }

  const managerIdForPython = 4;
  const pythonScriptAbsolutePath = path.join(__dirname, "..", "Python", "Constraints.py");
  const command = `python "${pythonScriptAbsolutePath}" --mode manual --manager-id ${managerIdForPython} --target-week ${targetWeekStartDate}`;

  console.log(`Executing Python script for hotel ${hotelName}: ${command}`);

  exec(command, { timeout: 300000 }, (error, stdout, stderr) => {
    if (error) {
      console.error(`Error executing Python script for ${hotelName}: ${error.message}`);
      console.error(`Python stderr: ${stderr}`);
      return res.status(500).json({
        success: false,
        message: "Error running the scheduler algorithm.",
        errorDetails: error.message,
        pythonStderr: stderr
      });
    }

    console.log(`Python script stdout for ${hotelName}:\n${stdout}`);
    if (stderr && stderr.trim() !== "") {
      console.warn(`Python script stderr (non-fatal) for ${hotelName}:\n${stderr}`);
    }

    res.json({
      success: true,
      message: "Scheduler algorithm completed successfully.",
      pythonOutput: stdout,
      pythonStderrOutput: stderr
    });
  });
});

// Fixed endpoint for mongojs (no Promise, no toArray)
app.get("/api/generated-schedules/:hotelName", (req, res) => {
  const hotelName = req.params.hotelName;

  // מצא את הסידור הנוכחי הכי חדש (Week: "Now")
  result_coll.find({ hotelName: hotelName, Week: "Now" }).sort({ generatedAt: -1 }).limit(1, (err, nowArr) => {
    if (err) {
      console.error(`Error fetching current schedule for ${hotelName}:`, err);
      return res.status(500).json({
        success: false,
        message: "Error fetching current schedule",
        error: err.message
      });
    }

    const nowSchedule = nowArr && nowArr.length > 0 ? nowArr[0] : null;

    // מצא את 5 הסידורים הקודמים האחרונים (Week: "Old")
    result_coll.find({ hotelName: hotelName, Week: "Old" }).sort({ generatedAt: -1 }).limit(5, (err2, oldSchedules) => {
      if (err2) {
        console.error(`Error fetching old schedules for ${hotelName}:`, err2);
        return res.status(500).json({
          success: false,
          message: "Error fetching old schedules",
          error: err2.message
        });
      }

      if (!nowSchedule && (!oldSchedules || oldSchedules.length === 0)) {
        return res.status(404).json({
          success: false,
          message: `No generated schedules found for hotel ${hotelName}.`,
          now: null,
          old: []
        });
      }

      res.json({
        success: true,
        now: nowSchedule,
        old: oldSchedules || [],
        idToName: nowSchedule?.idToName || {}
      });
    });
  });
});

// מוסיף נתיב חדש לקבלת תוצאות שיבוץ עם בעיות
app.get("/schedule-result/:hotelName", (req, res) => {
  const hotelName = req.params.hotelName;

  result_coll.findOne({ hotelName: hotelName, Week: "Now" }, (err, resultDoc) => {
    if (err) {
      console.error("❌ Error fetching result:", err);
      return res.status(500).json({ message: "Database error" });
    }

    if (!resultDoc) {
      return res.status(404).json({ message: "No schedule result found" });
    }

    res.json({
      status: resultDoc.status || "unknown",
      notes: resultDoc.notes || [],
      generatedAt: resultDoc.generatedAt,
    });
  });
});
app.get("/api/announcements", (req, res) => {
  announcements_coll.find().sort({ date: -1 }).limit(10, (err, docs) => {
    if (err) {
      return res.status(500).json({ success: false, message: "DB error" });
    }
    res.json({ success: true, announcements: docs });
  });
});

app.post("/api/announcements", (req, res) => {
  const { message } = req.body;
  if (!message) {
    return res.status(400).json({ success: false, message: "Missing message" });
  }
  const doc = { message, date: new Date() };
  announcements_coll.insert(doc, (err, result) => {
    if (err) {
      return res.status(500).json({ success: false });
    }
    res.json({ success: true, inserted: doc });
  });
});
app.delete("/api/announcements/:id", (req, res) => {
  const id = req.params.id;
  if (!id) return res.status(400).json({ success: false });

  announcements_coll.remove({ _id: mongojs.ObjectId(id) }, (err, result) => {
    if (err) return res.status(500).json({ success: false });
    res.json({ success: true });
  });
});


const PORT = process.env.PORT || 3002;
app.listen(PORT, "0.0.0.0", () => {
  console.log(`🚀 Server running on port ${PORT}. Accessible on your local network.`);
});