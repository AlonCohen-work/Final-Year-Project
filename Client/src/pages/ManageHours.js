import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import '../styles/ManageHours.css';

const ManageHours = () => {
  const [schedule, setSchedule] = useState({
    sunday: { enabled: false, from: '', until: '' },
    monday: { enabled: false, from: '', until: '' },
    tuesday: { enabled: false, from: '', until: '' },
    wednesday: { enabled: false, from: '', until: '' },
    thursday: { enabled: false, from: '', until: '' },
    friday: { enabled: false, from: '', until: '' },
    saturday: { enabled: false, from: '', until: '' },
  });

  const navigate = useNavigate();

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch('http://localhost:3002/manage-hours/get');
        const data = await response.json();
        setSchedule(data);
      } catch (error) {
        console.error('Error loading schedule:', error);
      }
    };
    fetchData();
  }, []);

  const toggleDay = (day) => {
    setSchedule((prev) => ({
      ...prev,
      [day]: { ...prev[day], enabled: !prev[day].enabled, from: '', until: '' },
    }));
  };

  const handleTimeChange = (day, field, value) => {
    setSchedule((prev) => ({
      ...prev,
      [day]: { ...prev[day], [field]: value },
    }));
  };

  const saveAllDays = async () => {
    const enabledDays = Object.entries(schedule).filter(([_, value]) => value.enabled);

    if (enabledDays.length === 0) {
      alert('No days to save. Please enable at least one day.');
      return;
    }

    for (const [day, { from, until }] of enabledDays) {
      if (!from || !until) {
        alert(`Please fill both 'From' and 'Until' fields for ${day}.`);
        return;
      }
      if (from >= until) {
        alert(`'From' time must be earlier than 'Until' time for ${day}.`);
        return;
      }
    }

    try {
      const responses = await Promise.all(
        enabledDays.map(([day, { from, until }]) =>
          fetch('http://localhost:3002/manage-hours/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ day, from, until }),
          })
        )
      );

      const failedDays = [];
      for (let i = 0; i < responses.length; i++) {
        if (!responses[i].ok) {
          failedDays.push(enabledDays[i][0]);
        }
      }

      if (failedDays.length > 0) {
        alert(`Failed to save: ${failedDays.join(', ')}`);
      } else {
        alert('All days saved successfully.');
        navigate('/home'); // מעבר לעמוד הבית
      }
    } catch (error) {
      console.error('Error saving days:', error);
      alert('An error occurred while saving.');
    }
  };

  return (
    <div className="manage-hours-container">
      <div className="manage-hours-form">
        <h2>Manage Working Hours</h2>
        {Object.keys(schedule).map((day) => (
          <div key={day} className="day-row">
            <label>{day.charAt(0).toUpperCase() + day.slice(1)}:</label>
            <button onClick={() => toggleDay(day)}>
              {schedule[day].enabled ? 'Disable' : 'Enable'}
            </button>
            <input
              type="time"
              disabled={!schedule[day].enabled}
              value={schedule[day].from}
              onChange={(e) => handleTimeChange(day, 'from', e.target.value)}
            />
            <input
              type="time"
              disabled={!schedule[day].enabled}
              value={schedule[day].until}
              onChange={(e) => handleTimeChange(day, 'until', e.target.value)}
            />
          </div>
        ))}
        <button className="save-all-btn" onClick={saveAllDays}>
          Save All
        </button>
      </div>
    </div>
  );
};

export default ManageHours;