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
  const hotelName = req.params.hotelName;
  const { schedule } = req.body;

  if (!schedule || typeof schedule !== 'object') {
    return res.status(400).json({ success: false, message: "Schedule data is missing or invalid." });
  }

  Workplace_coll.updateOne(
    { hotelName: hotelName },
    { $set: { schedule: schedule } },
    { upsert: true },
    (err, result) => {
      if (err) {
        console.error(`Error saving schedule to Workplace_coll for ${hotelName}:`, err);
        return res.status(500).json({ success: false, message: "Error saving schedule data." });
      }
      if (result.acknowledged && (result.matchedCount > 0 || result.upsertedCount > 0)) {
        console.log(`Schedule saved successfully for ${hotelName}.`);
        res.status(200).json({ success: true, message: "Schedule requirements saved successfully." });
      } else {
        console.log(`Workplace not found for hotelName: ${hotelName} or no changes made.`);
        return res.status(404).json({ success: false, message: "Workplace not found or no changes applied." });
      }
    }
  );
});

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

  result_coll.findOne({ hotelName: hotelName, Week: "Now" }, (err, nowSchedule) => {
    if (err) {
      console.error(`Error fetching current schedule for ${hotelName}:`, err);
      return res.status(500).json({
        success: false,
        message: "Error fetching current schedule",
        error: err.message
      });
    }
    result_coll.find({ hotelName: hotelName, Week: "Old" })
      .sort({ generatedAt: -1 })
      .limit(5, (err2, oldSchedules) => {
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
          idToWorker: nowSchedule?.idToWorker || {}
        });
      });
  });
});

// Start server
const PORT = process.env.PORT || 3002;
app.listen(PORT, "0.0.0.0", () => {
  console.log(`🚀 Server running on port ${PORT}. Accessible on your local network.`);
});