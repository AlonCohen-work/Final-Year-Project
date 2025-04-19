import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import "../styles/EmployeeRequest.css";

const EmployeeRequest = () => {
  const [userId, setUserId] = useState(null);
  const [selectedDays, setSelectedDays] = useState([]);
  const navigate = useNavigate();

  useEffect(() => {
    const userData = JSON.parse(localStorage.getItem("user"));
    if (userData && userData.id) {
      setUserId(userData.id);
    } else {
      console.error("User data not found in localStorage.");
      navigate("/login");
    }
  }, [navigate]);

  const daysOfWeek = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
  const shiftTypes = ["Morning", "Afternoon","Evening"];

  const handleDayCheckboxChange = (day) => {
    setSelectedDays((prevSelectedDays) => {
      const updatedDays = [...prevSelectedDays];
      const dayIndex = updatedDays.findIndex((d) => d.day === day);

      if (dayIndex !== -1) {
        updatedDays.splice(dayIndex, 1); // Remove day if exists
      } else {
        updatedDays.push({ day, shifts: [] }); // Add day with no shifts
      }
      return updatedDays;
    });
  };

  const handleShiftCheckboxChange = (day, shift) => {
    setSelectedDays((prevSelectedDays) => {
      const updatedDays = [...prevSelectedDays];
      const dayIndex = updatedDays.findIndex((d) => d.day === day);

      if (dayIndex !== -1) {
        const shifts = updatedDays[dayIndex].shifts;
        if (shifts.includes(shift)) {
          updatedDays[dayIndex].shifts = shifts.filter((s) => s !== shift); // Remove shift
        } else {
          updatedDays[dayIndex].shifts.push(shift); // Add shift
        }
      }
      return updatedDays;
    });
  };

  const handleSend = async () => {
    if (!userId) {
      console.error("User ID is not defined.");
      return;
    }

    // Add default shifts for days without specific shifts
    const requestData = selectedDays.map((d) => ({
      day: d.day,
      shifts: d.shifts.length > 0 ? d.shifts : shiftTypes, // Add default shifts if none selected
    }));

    try {
      const response = await fetch("/EmployeeRequest", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          userId,
          selectedDays: requestData,
        }),
      });

      if (response.ok) {
        console.log("Data sent successfully.");
        navigate("/home");
      } else {
        const errorMessage = await response.text();
        console.error("Server response:", errorMessage);
      }
    } catch (error) {
      console.error("An error occurred:", error);
    }
  };

  return (
    <div className="employee-request">
      <h1>Employee Request</h1>
      <p>Select the days and shifts you are available:</p>
      <table className="availability-table">
        <thead>
          <tr>
            <th>Day</th>
            <th>Available</th>
            {shiftTypes.map((shift) => (
              <th key={shift}>{shift}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {daysOfWeek.map((day) => (
            <tr
              key={day}
              className={selectedDays.some((d) => d.day === day) ? "selected-row" : ""}
            >
              <td>{day}</td>
              <td>
                <input
                  type="checkbox"
                  onChange={() => handleDayCheckboxChange(day)}
                  checked={selectedDays.some((d) => d.day === day)}
                />
              </td>
              {shiftTypes.map((shift) => (
                <td key={shift}>
                  <input
                    type="checkbox"
                    onChange={() => handleShiftCheckboxChange(day, shift)}
                    checked={
                      selectedDays.find((d) => d.day === day)?.shifts.includes(shift) || false
                    }
                    disabled={!selectedDays.some((d) => d.day === day)}
                  />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      <button
        className="send-button"
        onClick={handleSend}
        disabled={selectedDays.length === 0}
      >
        Send
      </button>
    </div>
  );
};

export default EmployeeRequest;
