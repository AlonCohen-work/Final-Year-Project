const express = require("express");
const mongojs = require("mongojs");
const cors = require("cors");
const app = express();

app.use(express.json());
app.use(cors());

// Connect to MongoDB Atlas
const db = mongojs(
  "mongodb+srv://alon123179:23892389Aa@cluster0.arcpa.mongodb.net/people?retryWrites=true&w=majority"
);
const people_coll = db.collection("people");
const Workplace_coll = db.collection("Workplace");

// MongoDB Connection Events
db.on("connect", () => {
  console.log("Connected to MongoDB Atlas");
});

db.on("error", (err) => {
  console.error("Database connection error:", err);
});

// Login endpoint
app.post("/login", (req, res) => {
  const { id, password } = req.body;
  console.log("📩 Received login request:", req.body);

  const numericId = parseInt(id);
  if (isNaN(numericId)) return res.status(400).send("Invalid ID format");

  people_coll.findOne({ _id: numericId }, (err, user) => {
    if (err) {
      console.error("❌ Database error:", err);
      return res.status(500).send("Database error");
    }

    if (user && user.password === password) {
      Workplace_coll.findOne(
        { hotelName: user.Workplace },
        (hotelErr, hotelData) => {
          if (hotelErr) {
            console.error("❌ Error retrieving schedule:", hotelErr);
            return res.status(500).send("Error retrieving data");
          }

          res.json({
            success: true,
            id: user._id,
            name: user.name,
            job: user.job,
            Workplace: user.Workplace,
            ShiftManager: user.ShiftManager,
            WeaponCertified:user.WeaponCertified,
            schedule: hotelData ? hotelData.schedule : {},
          });
        }
      );
    } else {
      console.log(`❌ Login failed for user: ${id}`);
      res.json({ success: false, message: "Invalid ID or password" });
    }
  });
});

// EmployeeRequest endpoint
app.post("/EmployeeRequest", (req, res) => {
  const { userId, selectedDays } = req.body;

  if (!userId || !Array.isArray(selectedDays))
    return res.status(400).send("Invalid data format");

  const numericId = parseInt(userId, 10);
  if (isNaN(numericId)) return res.status(400).send("Invalid userId format");

  people_coll.findOne({ _id: numericId }, (err, user) => {
    if (err) {
      console.error("Database error:", err);
      return res.status(500).send("Database error");
    }

    if (!user) {
      console.log(`User with ID ${numericId} not found.`);
      return res.status(404).send("User not found");
    }

    people_coll.updateOne(
      { _id: numericId },
      { $set: { selectedDays } },
      (updateErr) => {
        if (updateErr) {
          console.error("Error during update:", updateErr);
          return res.status(500).send("Error updating data");
        }

        console.log(
          `User ${userId} updated successfully with selectedDays:`,
          selectedDays
        );
        res.status(200).send("Days updated successfully");
      }
    );
  });
});
// GET availability for a user
app.get("/EmployeeRequest", (req, res) => {
  const userId = parseInt(req.query.userId);
  if (isNaN(userId)) {
    return res.status(400).send("Invalid userId format");
  }

  people_coll.findOne({ _id: userId }, (err, user) => {
    if (err) {
      console.error("❌ Error fetching user:", err);
      return res.status(500).send("Database error");
    }

    if (!user) {
      return res.status(404).send("User not found");
    }

    const selectedDays = user.selectedDays || [];
    res.json({ selectedDays });
  });
});

app.get("/get-latest-result/:hotelName", (req, res) => {
  const hotelName = req.params.hotelName;

  db.collection("result")
    .find({ hotelName })
    .sort({ generatedAt: -1 })
    .limit(1)
    .toArray((err, results) => {
      if (err || !results.length) return res.status(404).send("No result found");
      res.json(results[0]);
    });
});

app.post("/save-schedule/:hotelName", (req, res) => {
  const hotelName = req.params.hotelName;
  const schedule = req.body.schedule;

  Workplace_coll.updateOne(
    { hotelName },
    { $set: { schedule } },
    { upsert: true },
    (err) => {
      if (err) return res.status(500).send("Error saving data");
      res.status(200).send("Schedule saved successfully");
    }
  );
});

app.get("/get-schedule/:hotelName", (req, res) => {
  const hotelName = req.params.hotelName;

  Workplace_coll.findOne({ hotelName }, (err, data) => {
    if (err || !data) return res.status(404).send("No schedule found");
    res.json({ schedule: data.schedule });
  });
});

// Start the server
const PORT = process.env.PORT || 3002;
app.listen(PORT, "0.0.0.0", () => {
  console.log(`🚀 Server running on port ${PORT}`);
});
