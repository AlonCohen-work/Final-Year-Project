import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import "../styles/EmployeeRequest.css";

const EmployeeRequest = ({ userId }) => {
  const daysOfWeek = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
  const [selectedDays, setSelectedDays] = useState([]);
  const navigate = useNavigate();

  const handleCheckboxChange = (day) => {
    setSelectedDays((prevSelectedDays) =>
      prevSelectedDays.includes(day)
        ? prevSelectedDays.filter((d) => d !== day) // Remove the day
        : [...prevSelectedDays, day] // Add the day
    );
  };

  const handleSend = async () => {
    try {
      const response = await fetch("http://localhost:3002/api/employee-requests", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ userId, selectedDays }),
      });

      if (response.ok) {
        navigate("/home"); // Redirect to home page
      } else {
        console.error("Failed to send data to the server.");
      }
    } catch (error) {
      console.error("An error occurred while sending the data:", error);
    }
  };

  return (
    <div className="employee-request">
      <h1>Employee Request</h1>
      <p>Select the days you are available:</p>
      <table className="availability-table">
        <thead>
          <tr>
            <th>Day</th>
            <th>Available</th>
          </tr>
        </thead>
        <tbody>
          {daysOfWeek.map((day) => (
            <tr key={day} className={selectedDays.includes(day) ? "selected-row" : ""}>
              <td>{day}</td>
              <td>
                <input
                  type="checkbox"
                  onChange={() => handleCheckboxChange(day)}
                  checked={selectedDays.includes(day)}
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <button className="send-button" onClick={handleSend}>
        Send
      </button>
    </div>
  );
};

export default EmployeeRequest;
