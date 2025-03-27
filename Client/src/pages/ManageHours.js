import React, { useState, useEffect } from 'react';
import '../styles/ManageHours.css';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';

const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
const shifts = ['Morning', 'Afternoon', 'Evening'];
const defaultPositions = ['Control', 'Patrol', 'Entrance Security', 'Shift Supervisor'];

const createInitialSchedule = () => {
  const schedule = {};
  shifts.forEach((shift) => {
    schedule[shift] = {};
    defaultPositions.forEach((position) => {
      schedule[shift][position] = {};
      days.forEach((day) => {
        schedule[shift][position][day] = {
          noWeapon: 0,
          weapon: 0,
        };
      });
    });
  });
  return schedule;
};

const ManageHours = () => {
  const navigate = useNavigate();
  const [schedule, setSchedule] = useState(createInitialSchedule());

  const user = JSON.parse(localStorage.getItem('user'));
  const hotelName = user ? user.Workplace : '';

  useEffect(() => {
    if (hotelName) {
      axios.get(`/get-schedule/${hotelName}`).then(res => {
        setSchedule(res.data.schedule);
      }).catch(() => {
        setSchedule(createInitialSchedule());
      });
    } else {
      alert("Hotel name not found in localStorage!");
    }
  }, [hotelName]);

  const handleChange = (shift, position, day, weaponType, value) => {
    setSchedule(prev => ({
      ...prev,
      [shift]: {
        ...prev[shift],
        [position]: {
          ...prev[shift][position],
          [day]: {
            ...prev[shift][position][day],
            [weaponType]: value
          }
        }
      }
    }));
  };

  const addPosition = (shift) => {
    const newPosition = prompt("Enter new position name:");
    if (newPosition) {
      setSchedule(prev => ({
        ...prev,
        [shift]: {
          ...prev[shift],
          [newPosition]: days.reduce((acc, day) => ({
            ...acc,
            [day]: { noWeapon: 0, weapon: 0 }
          }), {})
        }
      }));
    }
  };

  const removePosition = (shift, position) => {
    setSchedule(prev => {
      const updated = { ...prev };
      delete updated[shift][position];
      return updated;
    });
  };

  const saveSchedule = () => {
    if (hotelName) {
      axios.post(`/save-schedule/${hotelName}`, { schedule })
        .then(() => {
          alert("work place restin saved successfully!");
          console.log("Data work place successfully.");

          navigate("/home");
        })
        .catch(() => alert("Error saving schedule."));
    } else {
      alert("Hotel name not found in localStorage!");
    }
  };

  return (
    <div className="manage-hours-container">
      <div className="manage-hours-form">
        <h2>Manage Schedule - {hotelName}</h2>
        {shifts.map(shift => (
          <div key={shift}>
            <h3>{shift} Shift</h3>
            <table className="schedule-table">
              <thead>
                <tr>
                  <th rowSpan="2">Position</th>
                  {days.map(day => <th colSpan="2" key={day}>{day}</th>)}
                  <th rowSpan="2">Actions</th>
                </tr>
                <tr>
                  {days.map(day => (
                    <React.Fragment key={`${day}-sub`}>
                      <th>No Weapon</th>
                      <th>Weapon</th>
                    </React.Fragment>
                  ))}
                </tr>
              </thead>
              <tbody>
                {Object.keys(schedule[shift]).map((position) => (
                  <tr key={position}>
                    <td>{position}</td>
                    {days.map(day => (
                      <React.Fragment key={`${shift}-${position}-${day}`}>
                        <td className={schedule[shift][position][day].noWeapon > 0 ? 'selected-row' : ''}>
                          <input type="number" min="0" value={schedule[shift][position][day].noWeapon}
                                 onChange={(e) => handleChange(shift, position, day, 'noWeapon', parseInt(e.target.value) || 0)} />
                        </td>
                        <td className={schedule[shift][position][day].weapon > 0 ? 'selected-row' : ''}>
                          <input type="number" min="0" value={schedule[shift][position][day].weapon}
                                 onChange={(e) => handleChange(shift, position, day, 'weapon', parseInt(e.target.value) || 0)} />
                        </td>
                      </React.Fragment>
                    ))}
                    <td><button className="remove-position" onClick={() => removePosition(shift, position)}>X</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
            <button className="add-position" onClick={() => addPosition(shift)}>+ Add Position</button>
          </div>
        ))}
        <button className="save-all" onClick={saveSchedule}>Save All</button>
      </div>
    </div>
  );
};

export default ManageHours;
