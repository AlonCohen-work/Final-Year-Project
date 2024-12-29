import React from "react";
import { Route, Routes, Navigate } from "react-router-dom";

import Navbar from "./components/Navbar";
import HomePage from "./components/HomePage";
import Login from "./components/Login";

import WeekleyScu from "./pages/WeekleyScu";  // Corrected import path
import Payroll from "./pages/Payroll";        // Corrected import path
import Shiftswap from "./pages/Shiftswap";    // Corrected import path
import ManageHours from "./pages/ManageHours";

function App() {
  return (
    <>
      <Navbar />
      {/* Define Routes for Home, Login, and other pages */}
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<Navigate to="/login" replace />} />
        <Route path="/home" element={<HomePage />} />
        <Route path="/weekleyScu" element={<WeekleyScu />} />
        <Route path="/payroll" element={<Payroll />} />
        <Route path="/shiftswap" element={<Shiftswap />} />
        <Route path="/manage-hours" element={<ManageHours />} />
      </Routes>
    </>
  );
}

export default App;
