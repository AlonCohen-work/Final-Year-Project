const express = require("express");
const mongojs = require("mongojs");
const cors = require("cors");
const app = express();
const { Client } = require("pg"); // connect to PostgreSQL

app.use(express.json());
app.use(cors());

// Connect to MongoDB Atlas
const db = mongojs("mongodb+srv://alon123179:23892389Aa@cluster0.arcpa.mongodb.net/people?retryWrites=true&w=majority");
const people_coll = db.collection("people");

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
  if (isNaN(numericId)) {
    return res.status(400).send("Invalid ID format");
  }

  people_coll.findOne({ _id: numericId }, (err, user) => {
    if (err) {
      console.error("❌ Database error:", err);
      return res.status(500).send("Database error");
    }

    if (user) {
      if (user.password === password) {
        console.log(`✅ Login successful for user: ${id}`);

        const responseData = {
          success: true,
          id: user._id,
        };

        if (user.name) {
          responseData.name = user.name;
        }

        if (user.job) {
          responseData.job = user.job;
        }

        res.json(responseData);
      } else {
        console.log(`❌ Incorrect password for user: ${id}`);
        res.json({ success: false, message: "Invalid ID or password" });
      }
    } else {
      console.log(`❌ User not found: ${id}`);
      res.json({ success: false, message: "Invalid ID or password" });
    }
  });
});

app.post("/EmployeeRequest", (req, res) => {
  const { userId, selectedDays } = req.body;

  // Validate request data
  if (!userId || !Array.isArray(selectedDays)) {
    return res.status(400).send("Invalid data format");
  }

  const numericId = parseInt(userId, 10);
  if (isNaN(numericId)) {
    return res.status(400).send("Invalid userId format");
  }

  // Find user in the database
  people_coll.findOne({ _id: numericId }, (err, user) => {
    if (err) {
      console.error("Database error:", err);
      return res.status(500).send("Database error");
    }

    if (!user) {
      console.log(`User with ID ${numericId} not found.`);
      return res.status(404).send("User not found");
    }

    // Update selectedDays for the user
    people_coll.updateOne(
      { _id: numericId },
      { $set: { selectedDays } },
      (updateErr) => {
        if (updateErr) {
          console.error("Error during update:", updateErr);
          return res.status(500).send("Error updating data");
        }


        console.log(`User ${userId} updated successfully with selectedDays:`, selectedDays);
        res.status(200).send("Days updated successfully");
      }
    );
  });
});

// Define connection between PostgreSQL database and the server
const postgresClient = new Client({
  user: "postgres",
  host: "192.168.7.1,
  database: "hotel_scheduling",
  password: "26101977",
  port: 5432,
});

// Connect to PostgreSQL
postgresClient
  .connect()
  .then(() => console.log("Connected to PostgreSQL"))
  .catch((err) => console.error("Error connecting to PostgreSQL", err.stack));

// Start the server
const PORT = process.env.PORT || 3002;
app.listen(PORT, () => {
  console.log(`🚀 Server running on port ${PORT}`);
});

// get data from postgersql table of legal consrains
app.get("/get-legal_constraints", async(req,res)=>{
  try{
      const result = await postgresClient.query(" SELECT * FROM legal_constraints");
      res.json({ success: true, data: result.rows});
  }catch(err){
      res.status(500).json({ success : false, error:err.message})
  }

});

// get data from table of place constraints
app.get("/get-location_constraints", async(req,res)=>{
   try{
       const resLocation= await postgresClient.query(" SELECT * FROM location_constraints");
       res.json({ success : true , data: resLocation.rows });
   }catch(err){
      res.status(500).json({ success: false , error:err.message  })
   }
});
