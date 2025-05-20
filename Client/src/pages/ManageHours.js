import React, { useState, useEffect, useCallback } from 'react';
import '../styles/ManageHours.css';
import axios from 'axios';
// useNavigate כנראה לא בשימוש בקומפוננטה הזו, אם כן - השאירי, אם לא - אפשר להסיר את השורה הבאה
// import { useNavigate } from 'react-router-dom';

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
          weapon: position === 'Shift Supervisor' ? 1 : 0,
        };
      });
    });
  });
  return schedule;
};

const getStartOfWeek = (date = new Date()) => {
  const d = new Date(date);
  const dayOfWeek = d.getDay();
  const diffToSunday = d.getDate() - dayOfWeek;
  d.setHours(0, 0, 0, 0);
  return new Date(d.setDate(diffToSunday));
};

const getWeekDateRangeString = (startDate) => {
  if (!startDate) return "Loading date range...";
  const start = new Date(startDate);
  const end = new Date(start);
  end.setDate(start.getDate() + 6);
  const formatDate = (dateObj) => {
    const day = String(dateObj.getDate()).padStart(2, '0');
    const month = String(dateObj.getMonth() + 1).padStart(2, '0');
    const year = dateObj.getFullYear();
    return `${day}/${month}/${year}`;
  };
  return `Planning Week: ${formatDate(start)} - ${formatDate(end)}`;
};

const ManageHours = () => {
  // const navigate = useNavigate(); // אם לא בשימוש, הסירי או השאירי בהערה

  const [schedule, setSchedule] = useState(createInitialSchedule());
  const [currentDayViewIndex, setCurrentDayViewIndex] = useState(0);
  const [targetWeekForPlanning, setTargetWeekForPlanning] = useState(null);

  // הגדרת user ו-hotelName כ-state
  const [user, setUser] = useState(null);
  const [hotelName, setHotelName] = useState('');

  const visibleDays = days.slice(currentDayViewIndex, currentDayViewIndex + 4);

  // useEffect לאתחול נתונים מ-localStorage וקביעת שבוע התכנון
  useEffect(() => {
    const storedUser = JSON.parse(localStorage.getItem('user'));
    if (storedUser) {
      setUser(storedUser);
      if (storedUser.Workplace) {
        setHotelName(storedUser.Workplace);
        console.log("ManageHours: hotelName set from localStorage:", storedUser.Workplace);
      } else {
        console.warn("ManageHours: Workplace not found in stored user from localStorage.");
        setHotelName('');
      }
    } else {
      console.warn("ManageHours: User not found in localStorage.");
    }

    const today = new Date();
    const startOfThisCalendarWeek = getStartOfWeek(today);
    const nextCalendarWeekStart = new Date(startOfThisCalendarWeek);
    nextCalendarWeekStart.setDate(startOfThisCalendarWeek.getDate() + 7);
    setTargetWeekForPlanning(nextCalendarWeekStart);
  }, []);

  const fetchCurrentRequirements = useCallback(() => {
    if (hotelName) {
      console.log("Fetching requirements for hotel (from state):", hotelName);
      axios.get(`/get-schedule/${encodeURIComponent(hotelName)}`)
        .then(res => {
          if (res.data && typeof res.data.schedule === 'object' && res.data.schedule !== null && Object.keys(res.data.schedule).length > 0) {
            setSchedule(res.data.schedule);
          } else {
            setSchedule(createInitialSchedule());
          }
        })
        .catch((err) => {
          console.error("Error fetching schedule for hotel:", hotelName, err.response ? err.response.data : err.message);
          setSchedule(createInitialSchedule());
        });
    }
  }, [hotelName]);

  useEffect(() => {
    if (hotelName) {
      fetchCurrentRequirements();
    }
  }, [hotelName, fetchCurrentRequirements]);

  const handleChange = (shift, position, day, weaponType, value) => {
    const numericValue = parseInt(value, 10);
    let finalValue = isNaN(numericValue) ? 0 : numericValue;
    if (position === 'Shift Supervisor' && weaponType === 'weapon' && finalValue < 1) {
      finalValue = 1;
    }
    setSchedule(prev => ({
      ...prev,
      [shift]: {
        ...prev[shift],
        [position]: {
          ...prev[shift][position],
          [day]: {
            ...prev[shift][position][day],
            [weaponType]: finalValue
          }
        }
      }
    }));
  };

  const handleGoToPreviousPlanningWeek = () => {
    if (targetWeekForPlanning) {
      const newStartDate = new Date(targetWeekForPlanning);
      newStartDate.setDate(targetWeekForPlanning.getDate() - 7);
      setTargetWeekForPlanning(newStartDate);
      setCurrentDayViewIndex(0);
    }
  };

  const handleGoToNextPlanningWeek = () => {
    if (targetWeekForPlanning) {
      const newStartDate = new Date(targetWeekForPlanning);
      newStartDate.setDate(targetWeekForPlanning.getDate() + 7);
      setTargetWeekForPlanning(newStartDate);
      setCurrentDayViewIndex(0);
    }
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
      console.log("Saving schedule for hotel (from state):", hotelName);
      axios.post(`/save-schedule/${encodeURIComponent(hotelName)}`, { schedule })
        .then(() => {
          alert(`Requirements saved (for week starting ${targetWeekForPlanning ? targetWeekForPlanning.toLocaleDateString('en-US') : 'unknown'})`);
        })
        .catch((err) => {
          console.error("Error saving schedule requirements for hotel:", hotelName, err.response ? err.response.data : err.message);
          alert("Error saving schedule requirements.");
        });
    } else {
      alert("Hotel name not found in state. Cannot save schedule.");
    }
  };

  const handleRunScheduler = async () => {
    if (!hotelName || !targetWeekForPlanning) {
      alert("Hotel name (from state) or target planning week is not set.");
      return;
    }
    const confirmRun = window.confirm(`Create schedule for week starting ${targetWeekForPlanning.toLocaleDateString('en-US')}? 
Make sure you have saved the current requirements.`);
    
    if (confirmRun) {
      try {
        const targetDateString = targetWeekForPlanning.toISOString().split('T')[0];
        console.log(`Requesting to run scheduler for hotel (from state): ${hotelName}, target week: ${targetDateString}`);
        const response = await axios.post(`/api/run-scheduler/${encodeURIComponent(hotelName)}`, {
          targetWeekStartDate: targetDateString
        });
        alert(response.data.message || "Scheduler request sent successfully.");
      } catch (error) {
        const errorMsg = error.response?.data?.stderr || error.response?.data?.message || error.message || "Unknown error";
        console.error("Error running scheduler for hotel:", hotelName, error.response ? error.response.data : error.message);
        alert(`Error running scheduler: ${errorMsg}`);
      }
    }
  };

  if (!user) {
    return <div>Loading user data or user not logged in... Please try logging in again.</div>;
  }
  if (user && !hotelName) {
    return <div>No workplace assigned to the logged-in user. Please check your profile.</div>;
  }

  return (
    <div className="manage-hours-container">
      <div className="manage-hours-form">
        <h2>Manage Requirements - {hotelName}</h2>

        <div className="week-navigation-controls" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', margin: '20px 0' }}>
          <button 
            onClick={handleGoToPreviousPlanningWeek} 
            style={{ 
              margin: '0 10px',
              backgroundColor: '#286090',
              color: 'white',
              border: 'none',
              padding: '8px 15px',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '14px'
            }}
          >
            {'<<'} Previous Week
          </button>
          {targetWeekForPlanning && (
            <h3 style={{ margin: '0 10px', fontSize: '1.4em', color: '#286090' }}>
              {getWeekDateRangeString(targetWeekForPlanning)}
            </h3>
          )}
          <button 
            onClick={handleGoToNextPlanningWeek} 
            style={{ 
              margin: '0 10px',
              backgroundColor: '#286090',
              color: 'white',
              border: 'none',
              padding: '8px 15px',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '14px'
            }}
          >
            Next Week {'>>'}
          </button>
        </div>

        {shifts.map(shift => (
          <div key={shift} className="shift-section">
            <h4>{shift} Shift</h4>
            <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '10px' }}>
              <button
                className="day-nav"
                onClick={() => setCurrentDayViewIndex(prev => Math.max(prev - 4, 0))}
                disabled={currentDayViewIndex === 0}
                style={{
                  backgroundColor: '#286090',
                  color: 'white',
                  border: 'none',
                  padding: '8px 15px',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  margin: '0 5px',
                  opacity: currentDayViewIndex === 0 ? 0.5 : 1
                }}
              >
                <span role="img" aria-label="Previous Day">⬅️</span>
              </button>
              <button
                className="day-nav"
                onClick={() => setCurrentDayViewIndex(prev => Math.min(prev + 4, days.length - 4))}
                disabled={currentDayViewIndex >= days.length - 4}
                style={{
                  backgroundColor: '#286090',
                  color: 'white',
                  border: 'none',
                  padding: '8px 15px',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  margin: '0 5px',
                  opacity: currentDayViewIndex >= days.length - 4 ? 0.5 : 1
                }}
              >
                <span role="img" aria-label="Next Day">➡️</span>
              </button>
            </div>

            <table className="schedule-table">
              <thead>
                <tr>
                  <th rowSpan="2">Position</th>
                  {visibleDays.map(day => <th colSpan="2" key={day}>{day}</th>)}
                  <th rowSpan="2">Actions</th>
                </tr>
                <tr>
                  {visibleDays.map(day => (
                    <React.Fragment key={`${day}-sub`}>
                      <th>No Weapon</th>
                      <th>Weapon</th>
                    </React.Fragment>
                  ))}
                </tr>
              </thead>

              <tbody>
                {Object.keys(schedule[shift] || {}).map((position) => (
                  <tr key={position}>
                    <td>{position}</td>
                    {visibleDays.map(day => (
                      <React.Fragment key={`${shift}-${position}-${day}`}>
                        <td className={schedule[shift]?.[position]?.[day]?.noWeapon > 0 ? 'selected-row' : ''}>
                          {position === 'Shift Supervisor' ? null : (
                            <input
                              type="number"
                              min="0"
                              value={schedule[shift]?.[position]?.[day]?.noWeapon || 0}
                              onChange={(e) => handleChange(shift, position, day, 'noWeapon', parseInt(e.target.value) || 0)}
                            />
                          )}
                        </td>
                        <td className={schedule[shift]?.[position]?.[day]?.weapon > 0 ? 'selected-row' : ''}>
                          <input
                            type="number"
                            min={position === 'Shift Supervisor' ? 1 : 0}
                            value={(position === 'Shift Supervisor' && (schedule[shift]?.[position]?.[day]?.weapon || 0) === 0) ? 1 : (schedule[shift]?.[position]?.[day]?.weapon || 0)}
                            onChange={(e) => handleChange(shift, position, day, 'weapon', parseInt(e.target.value) || 0)}
                          />
                        </td>
                      </React.Fragment>
                    ))}
                    <td><button className="remove-position" onClick={() => removePosition(shift, position)}>X</button></td>
                  </tr>
                ))}
              </tbody>
            </table>

            <button 
              className="add-position" 
              onClick={() => addPosition(shift)}
              style={{
                backgroundColor: '#286090',
                color: 'white',
                border: 'none',
                padding: '8px 15px',
                borderRadius: '4px',
                cursor: 'pointer',
                margin: '10px 0'
              }}
            >
              + Add Position
            </button>
          </div>
        ))}

        <div style={{ textAlign: 'center', marginTop: '30px', display: 'flex', justifyContent: 'space-around' }}>
          <button 
            className="save-all" 
            onClick={saveSchedule}
            style={{
              backgroundColor: '#286090',
              color: 'white',
              border: 'none',
              padding: '10px 20px',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '16px',
              minWidth: '200px'
            }}
          >
            Save Requirements
          </button>
          <button 
            onClick={handleRunScheduler} 
            className="run-scheduler-button"
            style={{
              backgroundColor: '#286090',
              color: 'white',
              border: 'none',
              padding: '10px 20px',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '16px',
              minWidth: '200px'
            }}
          >
            Create Schedule for Current Week
          </button>
        </div>
      </div>
    </div>
  );
};

export default ManageHours;