const express = require("express");
const mongojs = require("mongojs");
const cors = require("cors");
const { spawn } = require('child_process');
const path = require('path');
const moment = require("moment");

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

app.post("/api/run-scheduler/:hotelName", (req, res) => {
  const hotelName = req.params.hotelName;
  const { targetWeekStartDate } = req.body;

  console.log(`[Server] Received scheduler run request for hotel: "${hotelName}"`);

  if (!targetWeekStartDate || !/^\d{4}-\d{2}-\d{2}$/.test(targetWeekStartDate)) {
    console.error(`[Server] Invalid request: Missing or malformed targetWeekStartDate.`);
    return res.status(400).json({ message: "Invalid or missing targetWeekStartDate. Expected YYYY-MM-DD format." });
  }

  // Step 1: Find the manager for the given hotel to get a dynamic manager_id
  people_coll.findOne({ Workplace: hotelName, ShiftManager: true }, (err, manager) => {
    if (err) {
      console.error(`[Server] DB error finding manager for "${hotelName}":`, err);
      return res.status(500).json({ message: "Database error while searching for a manager." });
    }
    if (!manager) {
      console.error(`[Server] No manager found for hotel: "${hotelName}"`);
      return res.status(404).json({ message: `Configuration error: No manager found for hotel "${hotelName}". Cannot run scheduler.` });
    }

    const managerId = manager._id;
    console.log(`[Server] Found Manager ID: ${managerId}. Proceeding to run Python script.`);

    // Step 2: Set up the Python script execution in a secure way
    const pythonExecutable = 'python'; // More portable than a hardcoded path
    const pythonScriptPath = path.join(__dirname, '..', 'Python', 'Constraints.py');
    const args = [
      pythonScriptPath,
      '--mode', 'manual',
      '--manager-id', managerId.toString(),
      '--target-week', targetWeekStartDate
    ];

    console.log(`[Server] Spawning process: ${pythonExecutable} ${args.join(' ')}`);

    // Step 3: Use spawn to run the script and stream I/O
    const pythonProcess = spawn(pythonExecutable, args);

    let scriptOutput = '';
    let scriptError = '';

    // Capture standard output (for logging success)
    pythonProcess.stdout.on('data', (data) => {
      const outputChunk = data.toString();
      scriptOutput += outputChunk;
      console.log(`[Python STDOUT]: ${outputChunk.trim()}`);
    });

    // Capture standard error (for debugging failures)
    pythonProcess.stderr.on('data', (data) => {
      const errorChunk = data.toString();
      scriptError += errorChunk;
      console.error(`[Python STDERR]: ${errorChunk.trim()}`);
    });

    // Step 4: Handle the process exit and respond to the client
    pythonProcess.on('close', (code) => {
      console.log(`[Server] Python process finished with exit code ${code}.`);
      if (code === 0) {
        // Exit code 0 means success
        res.status(200).json({
          success: true,
          message: 'Scheduler algorithm completed successfully!',
          output: scriptOutput
        });
      } else {
        // Any other exit code means failure
        res.status(500).json({
          success: false,
          message: 'An error occurred while running the Python scheduler.',
          error: scriptError || 'Unknown error in Python script. See server console for details.'
        });
      }
    });

    // Handle errors in the spawn process itself (e.g., python not found)
    pythonProcess.on('error', (spawnError) => {
        console.error('[Server] Failed to start Python process:', spawnError);
        res.status(500).json({ success: false, message: 'Server configuration error: Failed to start the Python process.' });
    });
  });
});

/**
 * Endpoint to get all generated schedules for a hotel.
 * Slightly modified to always return the most relevant idToName map.
 */
app.get("/api/generated-schedules/:hotelName", (req, res) => {
    const hotelName = req.params.hotelName;
    const today = moment().startOf('day');
  
    // שלב 1: הלוגיקה למציאת "ציר" השבוע (שבת) נשארת זהה
    let currentWeekStart = moment(today).day(6); // 6 = Saturday
    if (currentWeekStart.isAfter(today)) {
      currentWeekStart = currentWeekStart.subtract(7, 'days');
    }
    const nextWeekStart = moment(currentWeekStart).add(7, 'days');
    
    // שלב 2: יצירת התאריכים הנכונים לחיפוש במסד הנתונים (ימי ראשון)
    // מוסיפים יום אחד לתאריכי השבת שחישבנו
    const currentWeekDbDate = moment(currentWeekStart).add(1, 'days').format('YYYY-MM-DD');
    const nextWeekDbDate = moment(nextWeekStart).add(1, 'days').format('YYYY-MM-DD');
  
    // שלב 3: שימוש בתאריכי יום ראשון בחיפוש אחר הסידורים הנוכחי והבא
    result_coll.find({
      hotelName: hotelName,
      relevantWeekStartDate: { $in: [currentWeekDbDate, nextWeekDbDate] }
    }).toArray((err, schedules) => {
      // טיפול בשגיאת מסד נתונים ראשונית
      if (err) {
        console.error("DB error fetching current/next schedules:", err);
        return res.status(500).json({ success: false, message: "Database error while fetching schedules." });
      }
      
      // שלב 4: מציאת הסידור הנוכחי והבא מתוך התוצאות, על סמך תאריכי יום ראשון
      let nowSchedule = schedules.find(s => s.relevantWeekStartDate === currentWeekDbDate) || null;
      let nextSchedule = schedules.find(s => s.relevantWeekStartDate === nextWeekDbDate) || null;
  
      // שלב 5: חיפוש אחר סידורים ישנים יותר
      // החיפוש לא כולל את התאריכים של הסידור הנוכחי והבא שכבר מצאנו
      result_coll.find({
        hotelName: hotelName,
        relevantWeekStartDate: { $nin: [currentWeekDbDate, nextWeekDbDate] }
      }).sort({ generatedAt: -1 }).limit(5).toArray((err2, oldSchedules) => {
        // טיפול בשגיאה בחיפוש השני
        if (err2) {
          console.error("DB error fetching old schedules:", err2);
          return res.status(500).json({ success: false, message: "Database error while fetching old schedules." });
        }
  
        // שלב 6: בחירת מפת השמות (idToName) הרלוונטית ביותר להצגה בצד הלקוח
        let idToNameMap = {};
        if (nowSchedule && nowSchedule.idToName) {
            idToNameMap = nowSchedule.idToName;
        } else if (nextSchedule && nextSchedule.idToName) {
            idToNameMap = nextSchedule.idToName;
        } else if (oldSchedules && oldSchedules.length > 0 && oldSchedules[0].idToName) {
            // אם אין סידור נוכחי או עתידי, ניקח את המפה מהסידור הישן האחרון
            idToNameMap = oldSchedules[0].idToName;
        }
  
        // שלב 7: שליחת התשובה המלאה לצד הלקוח
        res.json({
          success: true,
          now: nowSchedule,
          next: nextSchedule,
          old: oldSchedules || [],
          idToName: idToNameMap 
        });
      });
    });
  });


// Route to get current problematic schedule result for a hotel
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

// Retrieve the 10 most recent announcements (sorted by date descending)
app.get("/api/announcements", (req, res) => {
  announcements_coll.find().sort({ date: -1 }).limit(10, (err, docs) => {
    if (err) {
      return res.status(500).json({ success: false, message: "DB error" });
    }
    res.json({ success: true, announcements: docs });
  });
});

// Post a new announcement
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

// Delete an announcement by ID
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