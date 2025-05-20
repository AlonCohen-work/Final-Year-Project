import React, { useState, useEffect } from 'react';
import '../styles/ManageHours.css';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';

const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
const shifts = ['Morning', 'Afternoon', 'Evening']; // תיקנתי רווח שהיה פה
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

// פונקציות עזר לתאריכים - מחוץ לקומפוננטה
const getStartOfWeek = (date = new Date()) => {
  const d = new Date(date);
  const dayOfWeek = d.getDay(); // Sunday - 0, Monday - 1, etc.
  const diffToSunday = d.getDate() - dayOfWeek;
  d.setHours(0, 0, 0, 0); // איפוס שעה ליתר ביטחון
  return new Date(d.setDate(diffToSunday));
};

const getWeekDateRangeString = (startDate) => {
  if (!startDate) return "טוען טווח שבועי...";
  const start = new Date(startDate);
  const end = new Date(start);
  end.setDate(start.getDate() + 6); // Saturday

  const formatDate = (dateObj) => {
    const day = String(dateObj.getDate()).padStart(2, '0');
    const month = String(dateObj.getMonth() + 1).padStart(2, '0'); // Months are 0-indexed
    const year = dateObj.getFullYear();
    return `${day}/${month}/${year}`;
  };
  return `סידור לשבוע: ${formatDate(start)} - ${formatDate(end)}`;
};


const ManageHours = () => {
  const navigate = useNavigate();

  // State לניהול ה-schedule הכללי
  const [schedule, setSchedule] = useState(createInitialSchedule());

  // State לניהול איזה "קטע" של 4 ימים מוצג כרגע מהמערך 'days'
  const [currentDayViewIndex, setCurrentDayViewIndex] = useState(0);

  // --- חדש: State לניהול תאריך ההתחלה של השבוע המוצג ---
  const [displayedWeekStartDate, setDisplayedWeekStartDate] = useState(null);

  const user = JSON.parse(localStorage.getItem('user'));
  const hotelName = user ? user.Workplace : '';

  // המשתנה הזה עדיין שולט בתצוגת 4 הימים
  const visibleDays = days.slice(currentDayViewIndex, currentDayViewIndex + 4);

  // useEffect לאתחול ראשוני של displayedWeekStartDate
  useEffect(() => {
    if (displayedWeekStartDate === null) { // ירוץ רק פעם אחת בהתחלה
      const today = new Date();
      const startOfThisCalendarWeek = getStartOfWeek(today);

      const initialStartDateToDisplay = new Date(startOfThisCalendarWeek);
      // נניח שברירת המחדל היא להציג את "השבוע הבא"
      initialStartDateToDisplay.setDate(startOfThisCalendarWeek.getDate() + 7);

      setDisplayedWeekStartDate(initialStartDateToDisplay);
      setCurrentDayViewIndex(0); // חשוב לאפס את תצוגת הימים
    }
  }, []); // התלות הריקה מבטיחה ריצה חד פעמית

  // useEffect לטעינת ה-schedule מהשרת
  // כרגע, הוא עדיין טוען את ה-schedule הכללי של המלון.
  // בהמשך, נגרום לו להיות תלוי ב-displayedWeekStartDate.
  useEffect(() => {
    if (hotelName) {
      axios.get(`/get-schedule/${hotelName}`)
        .then(res => {
          if (res.data && typeof res.data.schedule === 'object' && res.data.schedule !== null) {
            setSchedule(res.data.schedule);
          } else {
            console.warn("Received invalid schedule data from server, using initial schedule.");
            setSchedule(createInitialSchedule());
          }
        })
        .catch((err) => {
          console.error("Error fetching schedule data:", err);
          setSchedule(createInitialSchedule());
        });
    } else {
      // הימנעי מ-alert אם המשתמש עדיין לא נטען מ-localStorage
      if (user && !hotelName) { // רק אם יש משתמש אבל אין לו שם מלון
          alert("Hotel name not found in localStorage for the current user!");
      }
    }
  }, [hotelName]); // כרגע תלוי רק ב-hotelName. בעתיד: [hotelName, displayedWeekStartDate]

  const handleChange = (shift, position, day, weaponType, value) => {
    // לוגיקת ה-handleChange שלך נשארת כפי שהיא
    if (position === 'Shift Supervisor' && weaponType === 'weapon' && value < 1) {
      value = 1; // אחמ"ש תמיד צריך לפחות 1 במשבצת הנשק שלו
    }
    setSchedule(prev => {
      // ודאי שהנתיבים קיימים לפני שאת מנסה לגשת אליהם
      const newShift = prev[shift] ? { ...prev[shift] } : {};
      const newPosition = newShift[position] ? { ...newShift[position] } : {};
      const newDay = newPosition[day] ? { ...newPosition[day] } : {};

      return {
        ...prev,
        [shift]: {
          ...newShift,
          [position]: {
            ...newPosition,
            [day]: {
              ...newDay,
              [weaponType]: parseInt(value, 10) || 0 // המרה למספר וערך ברירת מחדל
            }
          }
        }
      };
    });
  };

  const addPosition = (shift) => {
    // לוגיקת addPosition שלך נשארת כפי שהיא
    const newPositionName = prompt("Enter new position name:"); // שיניתי שם משתנה
    if (newPositionName) {
      setSchedule(prev => {
        const newShiftData = { ...(prev[shift] || {}) };
        newShiftData[newPositionName] = days.reduce((acc, day) => {
          acc[day] = { noWeapon: 0, weapon: 0 };
          return acc;
        }, {});
        return { ...prev, [shift]: newShiftData };
      });
    }
  };

  const removePosition = (shift, position) => {
    // לוגיקת removePosition שלך נשארת כפי שהיא
    setSchedule(prev => {
      const updatedSchedule = { ...prev };
      if (updatedSchedule[shift]) {
        const updatedShift = { ...updatedSchedule[shift] };
        delete updatedShift[position];
        updatedSchedule[shift] = updatedShift;
      }
      return updatedSchedule;
    });
  };

  const saveSchedule = () => {
    // לוגיקת saveSchedule שלך נשארת כפי שהיא כרגע
    // בעתיד, אולי נרצה לשלוח גם את displayedWeekStartDate לשרת
    if (hotelName) {
      axios.post(`/save-schedule/${hotelName}`, { schedule })
        .then(() => {
          alert("Workplace restrictions saved successfully!");
          console.log("Data for workplace saved successfully.");
          navigate("/home");
        })
        .catch(() => alert("Error saving schedule."));
    } else {
      alert("Hotel name not found in localStorage for saving!");
    }
  };
  
  return (
    <div className="manage-hours-container">
      <div className="manage-hours-form">
        <h2>Manage Schedule - {hotelName}</h2>

        {/* הצגת טווח התאריכים של השבוע */}
        {displayedWeekStartDate && (
          <h2 style={{ textAlign: 'center', margin: '20px 0', fontSize: '1.6em', color: '#337ab7' }}>
            {getWeekDateRangeString(displayedWeekStartDate)}
          </h2>
        )}

        {shifts.map(shift => (
          <div key={shift} className="shift-section"> {/* הוספתי class לכל מקטע משמרת */}
            <h3>{shift} Shift</h3>

            {/* כפתורי ניווט הימים (⬅️, ➡️) - נשארים לשליטה על תצוגת 4 הימים */}
            <div className="day-view-navigation"> {/* הוספתי class */}
              <button
                className="day-nav"
                onClick={() => setCurrentDayViewIndex(prev => Math.max(prev - 4, 0))}
                disabled={currentDayViewIndex === 0}
              >
                <span role="img" aria-label="Previous 4 Days">⬅️</span>
              </button>
              <button
                className="day-nav"
                onClick={() => setCurrentDayViewIndex(prev => Math.min(prev + 4, days.length - 4))}
                disabled={currentDayViewIndex >= days.length - 4}
              >
                <span role="img" aria-label="Next 4 Days">➡️</span>
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
                {/* חשוב לוודא ש-schedule[shift] קיים לפני הפעלת Object.keys */}
                {schedule && schedule[shift] && Object.keys(schedule[shift]).map((position) => (
                  <tr key={position}>
                    <td>{position}</td>
                    {visibleDays.map(day => {
                      // בודקים אם הנתיב המלא קיים באובייקט ה-schedule
                      const dayData = schedule[shift]?.[position]?.[day];
                      const noWeaponValue = dayData?.noWeapon || 0;
                      const weaponValue = dayData?.weapon || 0;

                      return (
                        <React.Fragment key={`${shift}-${position}-${day}`}>
                          <td className={noWeaponValue > 0 ? 'selected-row' : ''}>
                            {position === 'Shift Supervisor' ? <span> </span> : ( // אם זה אחמ"ש, לא מציגים input ל-noWeapon
                              <input
                                type="number"
                                min="0"
                                value={noWeaponValue}
                                onChange={(e) => handleChange(shift, position, day, 'noWeapon', e.target.value)}
                              />
                            )}
                          </td>
                          <td className={weaponValue > 0 ? 'selected-row' : ''}>
                            <input
                              type="number"
                              min={position === 'Shift Supervisor' ? 1 : 0}
                              // אם זה אחמ"ש והערך 0, קובעים ל-1 (כי הוא חייב להיות משובץ)
                              value={(position === 'Shift Supervisor' && weaponValue === 0) ? 1 : weaponValue}
                              onChange={(e) => handleChange(shift, position, day, 'weapon', e.target.value)}
                            />
                          </td>
                        </React.Fragment>
                      );
                    })}
                    <td><button className="remove-position" onClick={() => removePosition(shift, position)}>X</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
            <button className="add-position" onClick={() => addPosition(shift)}>+ Add Position</button>
          </div>
        ))}

        <button className="save-all" onClick={saveSchedule}>Save All Changes</button> {/* שיניתי טקסט */}
      </div>
    </div>
  );
};

export default ManageHours;