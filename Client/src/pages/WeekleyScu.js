import React, { useEffect, useState } from 'react';
import '../styles/WeekleyScu.css';
const SHIFTS = ['Morning', 'Afternoon', 'Evening'];

const isDateInWeekRange = (dateToCheck, weekStartDate) => {
  if (!weekStartDate) return false;
  const start = new Date(weekStartDate);
  start.setHours(0, 0, 0, 0);
  const end = new Date(start);
  end.setDate(start.getDate() + 6);
  return dateToCheck >= start && dateToCheck <= end;
};

const getWeekDateRangeStringForDisplay = (startDate) => {
  if (!startDate) return 'Date not available';

  let start;
  if (typeof startDate === 'string') {
    start = new Date(startDate);
    if (isNaN(start)) return 'Invalid date';
  } else if (startDate instanceof Date) {
    start = new Date(startDate);
  } else {
    return 'Unknown date';
  }

  // הוספת יום אחד לתאריך כדי שהשבוע יתחיל ביום ראשון שאחריו
  start.setDate(start.getDate() + 1);
  start.setHours(0, 0, 0, 0);

  const end = new Date(start);
  end.setDate(start.getDate() + 6);

  const formatDate = (dateObj) => {
    const day = String(dateObj.getDate()).padStart(2, '0');
    const month = String(dateObj.getMonth() + 1).padStart(2, '0');
    const year = dateObj.getFullYear();
    return `${day}/${month}/${year}`;
  };

  return `${formatDate(start)} - ${formatDate(end)}`;
};


const WeeklySchedule = () => {
  const [schedules, setSchedules] = useState({ latest: null, previous: [] });
  const [selectedSchedule, setSelectedSchedule] = useState(null);
  const [idToName, setIdToName] = useState({});
  const [viewMode, setViewMode] = useState('byDay');
  const [error, setError] = useState(null);


  const [user] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem('user'));
    } catch {
      return null;
    }
  });
  const hotelName = user?.Workplace || '';

  useEffect(() => {
    
    setError(null);

    fetch(`/api/generated-schedules/${encodeURIComponent(hotelName)}`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
        return res.json();
      })
      .then((data) => {
        const latestSchedule = data?.now || null;
        const previousSchedules = Array.isArray(data?.old) ? data.old : [];
        const nextSchedules = data.next ;
        const allSchedules = [];

        if (latestSchedule) allSchedules.push({ key: 'latest', schedule: latestSchedule });
        previousSchedules.forEach((sch, idx) => allSchedules.push({ key: idx, schedule: sch }));

        const today = new Date();
        today.setHours(0, 0, 0, 0);

        let foundKey = null;
        for (const item of allSchedules) {
          const weekStartStr = item.schedule?.relevantWeekStartDate;
          if (weekStartStr && isDateInWeekRange(today, weekStartStr)) {
            foundKey = item.key;
            break;
          }
        }

        setSchedules({
          latest: latestSchedule,
          previous: previousSchedules,
          next:nextSchedules,
        });
        setIdToName(data.idToName || {});

        const getNameOrKey = (key) => {
          if (!key) return key;
          return (data.idToName && data.idToName[key]) ? data.idToName[key] : key;
        };

        if (nextSchedules) {
          setSelectedSchedule(getNameOrKey('next'));
        } else if (foundKey !== null) {
          setSelectedSchedule(getNameOrKey(foundKey));
        } else {
          setSelectedSchedule('latest');
        }

      })
      .catch((err) => {
        console.error('Error loading schedules:', err);
        setError('Failed to load schedules. Please try again later.');
        setSchedules({ latest: null, previous: [] });
      })
      
  }, [user, hotelName]);

 const getWorkerName = (workerId) => {
  const strId = String(workerId);
  const name = idToName?.[strId];

  if (typeof name === 'string' && name.startsWith('No Worker')) return 'Empty';
  if (workerId < 0) return 'Empty';  // במקרה שיש id שלילי שלא נמצא
  return name || `ID: ${workerId}`;
};

const getWorkerClass = (name) => {
  if (!name || name === 'Empty' || name.includes('No Worker') || String(name).startsWith('ID: -')) 
    return 'worker-missing';
  if (name === user.name) return 'highlight-user';
  return 'worker-ok';
};



  const renderDayTable = (day, shifts) => {
    const positionsSet = new Set();
    SHIFTS.forEach((shift) => {
      (shifts[shift] || []).forEach((entry) => positionsSet.add(entry.position));
    });
    const positions = Array.from(positionsSet);

    return (
      <div className="day-section" key={day}>
        <h3>{day}</h3>
        <table className="schedule-grid">
          <thead>
            <tr>
              <th>Position</th>
              {SHIFTS.map((shift) => (
                <th key={shift}>{shift}</th>
              ))}
            </tr>
          </thead>
         <tbody>
  {positions.map((position) => (
    <tr key={position}>
      <td>{position}</td>
      {SHIFTS.map((shift) => {
        const entries = (shifts[shift] || []).filter((e) => e.position === position);

        return (
          <td key={shift}>
            {entries.length === 0 ? (
              '-'
            ) : (
              entries.map((entry, index) => {
                const name = getWorkerName(entry.worker_id);
                const className = getWorkerClass(name);
                return (
                  <span key={entry.worker_id} className={className}>
                    {name}
                    {index < entries.length - 1 ? ', ' : ''}
                  </span>
                );
              })
            )}
          </td>
        );
      })}
    </tr>
  ))}
</tbody>
        </table>
      </div>
    );
  };

  const renderWideTable = (schedule) => {
  if (!schedule || !schedule.schedule) return <p>No schedule found</p>;

  const days = Object.keys(schedule.schedule);

  return SHIFTS.map((shift) => {
    const positionsSet = new Set();
    days.forEach((day) => {
      (schedule.schedule[day][shift] || []).forEach((entry) => {
        positionsSet.add(entry.position);
      });
    });

    const positions = Array.from(positionsSet);

    return (
      <div className="day-section" key={shift}>
        <h3>{shift} Shift – Weekly View</h3>
        <table className="schedule-grid">
          <thead>
            <tr>
              <th>Position</th>
              {days.map((day) => (
                <th key={day}>{day}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {positions.map((position) => (
              <tr key={position}>
                <td>{position}</td>
                {days.map((day) => {
                  const entries = (schedule.schedule[day][shift] || []).filter(
                    (e) => e.position === position
                  );

                  return (
                    <td key={day}>
                      {entries.length === 0 ? (
                        '-'
                      ) : (
                        entries.map((entry, index) => {
                          const name = getWorkerName(entry.worker_id);
                          const className = getWorkerClass(name);
                          return (
                            <span key={entry.worker_id} className={className}>
                              {name}
                              {index < entries.length - 1 ? ', ' : ''}
                            </span>
                          );
                        })
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  });
};

  // Helper to get the relevant schedule
  const getCurrentSchedule = () => schedules.latest;
  const getPreviousSchedule = () => Array.isArray(schedules.previous) && schedules.previous.length > 0 ? schedules.previous[0] : null;
  const getNextSchedule = () => schedules.next || null; // If you have a next/future schedule, otherwise always null

  let scheduleToDisplay = null;
  if (selectedSchedule === 'current') {
    scheduleToDisplay = getCurrentSchedule();
  } else if (selectedSchedule === 'previous') {
    scheduleToDisplay = getPreviousSchedule();
  } else if (selectedSchedule === 'next') {
    scheduleToDisplay = getNextSchedule();
  }

  if (error) return <div className="error-message">{error}</div>;
  if (!hotelName && user) return <div className="error-message">User has no assigned workplace</div>;
  if (!user) return null;

  return (
    <div className="content-wrapper weekly-schedule-page">
      <h1>Work Schedule View - {hotelName}</h1>

      <div className="button-fixed-right">
         <button
          onClick={() => setSelectedSchedule('next')}
          className={selectedSchedule === 'next' ? 'active' : ''}
        >
          Next Week
        </button>
        <button
          onClick={() => setSelectedSchedule('current')}
          className={selectedSchedule === 'current' ? 'active' : ''}
        >
          Current Week
        </button>
        <button
          onClick={() => setSelectedSchedule('previous')}
          className={selectedSchedule === 'previous' ? 'active' : ''}
        >
          Previous Week
        </button>
        {scheduleToDisplay && (
          <button
            onClick={() => setViewMode((prevMode) => (prevMode === 'byDay' ? 'wide' : 'byDay'))}
            className="btn btn-toggle"
          >
            {viewMode === 'byDay' ? '🔄 Show by Week' : '📅 Show by Day'}
          </button>
        )}
      </div>

      {/* Display the selected schedule or a message */}
      {selectedSchedule === 'current' && !getCurrentSchedule() && (
        <div className="no-schedule-message">No schedule for the current week</div>
      )}
      {selectedSchedule === 'previous' && !getPreviousSchedule() && (
        <div className="no-schedule-message">No schedule for the previous week</div>
      )}
      {selectedSchedule === 'next' && !getNextSchedule() && (
        <div className="no-schedule-message">No schedule for the next week</div>
      )}
      {scheduleToDisplay && (
      <div className="schedule-content">
      <p className="schedule-header">
      Schedule for: {getWeekDateRangeStringForDisplay(scheduleToDisplay.relevantWeekStartDate)}
      {scheduleToDisplay.status === 'partial' && (
        <span className="partial-schedule-note">(Partial schedule)</span>
      )}
       </p>
          {viewMode === 'byDay'
            ? Object.entries(scheduleToDisplay.schedule).map(([day, shifts]) =>
                renderDayTable(day, shifts)
              )
            : renderWideTable(scheduleToDisplay)}
        </div>
      )}
    </div>
  );
};

export default WeeklySchedule;
