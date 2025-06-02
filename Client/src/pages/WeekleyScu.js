import React, { useEffect, useState } from 'react';
import '../styles/WeekleyScu.css';

const SHIFTS = ['Morning', 'Afternoon', 'Evening'];

const getStartOfWeek = (date = new Date()) => {
  const d = new Date(date);
  const dayOfWeek = d.getDay();
  const diffToSunday = d.getDate() - dayOfWeek;
  d.setHours(0, 0, 0, 0);
  return new Date(d.setDate(diffToSunday));
};

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
    start = getStartOfWeek(startDate);
    if (!start) return 'Invalid date';
  } else if (startDate instanceof Date) {
    start = new Date(startDate);
  } else {
    return 'Unknown date';
  }

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

const getWeekRangeFromGeneratedAt = (generatedAt) => {
  const date = new Date(generatedAt);
  const day = date.getDay();
  const daysToAdd = day === 0 ? 0 : 7 - day;
  const sunday = new Date(date);
  sunday.setDate(sunday.getDate() + daysToAdd);
  sunday.setHours(0, 0, 0, 0);

  const saturday = new Date(sunday);
  saturday.setDate(sunday.getDate() + 6);

  const format = (d) => {
    const dd = String(d.getDate()).padStart(2, '0');
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const yyyy = d.getFullYear();
    return `${dd}/${mm}/${yyyy}`;
  };

  return `${format(sunday)} - ${format(saturday)}`;
};

const WeeklySchedule = () => {
  const [schedules, setSchedules] = useState({ latest: null, previous: [] });
  const [selectedSchedule, setSelectedSchedule] = useState('current');
  const [idToName, setIdToName] = useState({});
  const [viewMode, setViewMode] = useState('byDay');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [missingNotes, setMissingNotes] = useState([]);

  const [user] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem('user'));
    } catch {
      return null;
    }
  });
  const hotelName = user?.Workplace || '';

  useEffect(() => {
    if (!user) {
      setIsLoading(false);
      return;
    }
    if (!hotelName) {
      setError('User has no assigned workplace');
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);

    fetch(`/api/generated-schedules/${encodeURIComponent(hotelName)}`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
        return res.json();
      })
      .then((data) => {
        const latestSchedule = data?.now || null;
        const previousSchedules = Array.isArray(data?.old) ? data.old : [];
        const allSchedules = [];

        if (latestSchedule) allSchedules.push({ key: 'latest', schedule: latestSchedule });
        previousSchedules.forEach((sch, idx) => allSchedules.push({ key: idx, schedule: sch }));

        const today = new Date();
        today.setHours(0, 0, 0, 0);
        const startOfCurrentWeek = getStartOfWeek(today);

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
        });

        setIdToName(data.idToName || {});
        setSelectedSchedule(foundKey !== null ? foundKey : 'latest');
      })
      .catch((err) => {
        console.error('Error loading schedules:', err);
        setError('Failed to load schedules. Please try again later.');
        setSchedules({ latest: null, previous: [] });
      })
      .finally(() => setIsLoading(false));
  }, [user, hotelName]);

  useEffect(() => {
    if (!hotelName) return;
    fetch(`/schedule-result/${encodeURIComponent(hotelName)}`)
      .then(res => res.json())
      .then(data => {
        if (data.notes && Array.isArray(data.notes)) {
          setMissingNotes(data.notes);
        } else {
          setMissingNotes([]);
        }
      })
      .catch(() => setMissingNotes([]));
  }, [hotelName]);

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


  const handleSelectSchedule = (key) => {
    setSelectedSchedule(key);
  };

  let currentScheduleToDisplay = null;
  if (selectedSchedule === 'latest') {
    currentScheduleToDisplay = schedules.latest;
  } else if (
    Array.isArray(schedules.previous) &&
    typeof selectedSchedule === 'number' &&
    schedules.previous[selectedSchedule]
  ) {
    currentScheduleToDisplay = schedules.previous[selectedSchedule];
  }

  const previousSchedules = Array.isArray(schedules.previous) ? schedules.previous : [];

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
                  const names = entries.map((entry) => getWorkerName(entry.worker_id)).join(', ');
                  return (
                    <td key={shift} className={getWorkerClass(names)}>
                      {names}
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
                    const entries = (schedule.schedule[day][shift] || []).filter((e) => e.position === position);
                    const names = entries.map((entry) => getWorkerName(entry.worker_id)).join(', ');
                    return (
                      <td key={day} className={getWorkerClass(names)}>
                        {names}
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

  // Helper: does user match the missing note (can work, but didn't request)
  const isNoteRelevantForUser = (note) => {
    if (!user) return false;
    // If manager, see all
    if (user.job && user.job.toLowerCase().includes('manager')) return true;
    // Check position
    if (user.job !== note.position) return false;
    // Check weapon requirement
    if (note.weapon && !user.WeaponCertified) return false;
    // Check if user already requested this shift
    if (Array.isArray(user.selectedDays)) {
      // selectedDays: [{ day: 'Monday', shifts: ['Morning', ...] }, ...]
      const [day, shift] = note.shift.split(' ');
      const dayObj = user.selectedDays.find(d => d.day === day);
      if (dayObj && Array.isArray(dayObj.shifts) && dayObj.shifts.includes(shift)) {
        return false; // already requested
      }
    }
    return true;
  };

  const filteredMissingNotes = user && user.job && user.job.toLowerCase().includes('manager')
    ? missingNotes
    : missingNotes.filter(isNoteRelevantForUser);

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

  if (isLoading) return <div className="loading-message">Loading schedules...</div>;
  if (error) return <div className="error-message">{error}</div>;
  if (!hotelName && user) return <div className="error-message">User has no assigned workplace</div>;
  if (!user) return null;

  return (
    <div className="content-wrapper weekly-schedule-page">
      <h1>Work Schedule View - {hotelName}</h1>

      {/* Show missing shifts warning if any, RTL and filtered */}
      {filteredMissingNotes.length > 0 && (
        <div className="missing-warning" style={{background:'#fff3cd',border:'1px solid #ffeeba',padding:'16px',marginBottom:'16px',borderRadius:'8px', direction:'rtl', textAlign:'right'}}>
          <h2 style={{color:'#856404'}}>שימו לב! יש חוסרים בשיבוץ:</h2>
          {user && user.job && user.job.toLowerCase().includes('manager') && (
            <div style={{fontWeight:'bold',marginBottom:'8px'}}>סה"כ חוסרים: {filteredMissingNotes.length}</div>
          )}
          <ul>
            {filteredMissingNotes.map((note, idx) => (
              <li key={idx}>
                חסר בתפקיד <b>{note.position}</b> במשמרת <b>{note.shift}</b> {note.weapon ? '(נדרש נשק)' : ''}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="button-fixed-right">
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

      {scheduleToDisplay && (
        <div className="schedule-content">
          <p style={{ textAlign: 'center', fontSize: '0.9em', color: '#555' }}>
            Schedule for: {getWeekDateRangeStringForDisplay(scheduleToDisplay.relevantWeekStartDate)}
            {scheduleToDisplay.status === 'partial' && (
              <span style={{ color: 'orange', marginLeft: '10px' }}>(Partial schedule)</span>
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
