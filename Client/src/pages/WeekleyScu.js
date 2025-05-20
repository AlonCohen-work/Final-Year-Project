import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import '../styles/WeekleyScu.css';

const SHIFTS = ['Morning', 'Afternoon', 'Evening'];

const getStartOfWeekFromYYYYMMDD = (yyyyMmDdStr) => {
    if (!yyyyMmDdStr || !/^\d{4}-\d{2}-\d{2}$/.test(yyyyMmDdStr)) {
        return null;
    }
    const parts = yyyyMmDdStr.split('-');
    return new Date(parseInt(parts[0], 10), parseInt(parts[1], 10) - 1, parseInt(parts[2], 10));
};

const getWeekDateRangeStringForDisplay = (startDate) => {
    if (!startDate) return "תאריך לא זמין";
    let start;
    if (typeof startDate === 'string') {
        start = getStartOfWeekFromYYYYMMDD(startDate);
        if (!start) return "תאריך לא תקין";
    } else if (startDate instanceof Date) {
        start = new Date(startDate);
    } else {
        return "תאריך לא ידוע";
    }
    
    start.setHours(0,0,0,0);
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

const buttonStyle = {
    background: '#286090',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    padding: '8px 18px',
    margin: '0 6px 8px 0',
    fontSize: '1em',
    cursor: 'pointer',
    minWidth: '120px',
    fontWeight: 600,
    boxShadow: '0 2px 6px rgba(40,96,144,0.08)'
};
const activeButtonStyle = {
    ...buttonStyle,
    background: '#1b4f72',
    border: '2px solid #1b4f72',
};
const toggleButtonStyle = {
    ...buttonStyle,
    background: '#117a8b',
    minWidth: '180px',
};

const WeekleyScu = () => {
    const navigate = useNavigate();
    const [schedules, setSchedules] = useState({ latest: null, previous: [] });
    const [selectedScheduleKey, setSelectedScheduleKey] = useState("latest");
    const [idToWorker, setIdToWorker] = useState({});
    const [viewMode, setViewMode] = useState("byDay");
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(null);

    const [user] = useState(() => {
        try {
            return JSON.parse(localStorage.getItem("user"));
        } catch {
            return null;
        }
    });
    const hotelName = user ? user.Workplace : '';

    useEffect(() => {
        if (!user || !hotelName) {
            setIsLoading(false);
            if (!hotelName && user) setError("למשתמש אין מקום עבודה משויך");
            return;
        }

        setIsLoading(true);
        setError(null);

        fetch(`/api/generated-schedules/${encodeURIComponent(hotelName)}`)
            .then((res) => res.json())
            .then((data) => {
                console.log("Received data:", data); // Debug log
                setSchedules({
                    latest: data && data.now ? data.now : null,
                    previous: Array.isArray(data && data.old) ? data.old : []
                });
                setIdToWorker(data && data.now && data.now.idToWorker ? data.now.idToWorker : {});
            })
            .catch((err) => {
                console.error("שגיאה בטעינת סידורים:", err);
                setError("טעינת הסידורים נכשלה. אנא נסה שוב מאוחר יותר");
                setSchedules({ latest: null, previous: [] });
            })
            .finally(() => {
                setIsLoading(false);
            });
    }, []);

    const getWorkerClass = (name) => {
        if (!name || name === "Empty" || String(name).startsWith("ID: -")) return "worker-missing";
        if (user && name === user.name) return "highlight-user";
        return "worker-ok";
    };

    const handleSelectSchedule = (key) => {
        setSelectedScheduleKey(key);
    };

    let currentScheduleToDisplay = null;
    if (selectedScheduleKey === "latest" && schedules.latest) {
        currentScheduleToDisplay = schedules.latest;
    } else if (Array.isArray(schedules.previous) && schedules.previous[selectedScheduleKey]) {
        currentScheduleToDisplay = schedules.previous[selectedScheduleKey];
    }

    const previousSchedules = Array.isArray(schedules.previous) ? schedules.previous : [];

    const renderDayTable = (day, shifts) => {
        const positionsSet = new Set();
        SHIFTS.forEach(shift => {
            (shifts[shift] || []).forEach(entry => positionsSet.add(entry.position));
        });
        const positions = Array.from(positionsSet);

        return (
            <div className="day-section" key={day}>
                <h3>{day}</h3>
                <table className="schedule-grid">
                    <thead>
                        <tr>
                            <th>תפקיד</th>
                            {SHIFTS.map(shift => <th key={shift}>{shift}</th>)}
                        </tr>
                    </thead>
                    <tbody>
                        {positions.map(position => (
                            <tr key={position}>
                                <td>{position}</td>
                                {SHIFTS.map(shift => {
                                    const entries = (shifts[shift] || []).filter(e => e.position === position);
                                    const names = entries.map(entry => {
                                        const worker = idToWorker?.[String(entry.worker_id)];
                                        return worker?.name || `ID: ${entry.worker_id}`;
                                    }).join(', ');
                                    return (
                                        <td key={shift} style={{ color: names.includes('ID:') ? 'red' : 'black' }}>
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
        if (!schedule || !schedule.schedule) return <p>לא נמצא סידור</p>;

        const days = Object.keys(schedule.schedule);

        return SHIFTS.map(shift => {
            const positionsSet = new Set();
            days.forEach(day => {
                (schedule.schedule[day][shift] || []).forEach(entry => {
                    positionsSet.add(entry.position);
                });
            });

            const positions = Array.from(positionsSet);

            return (
                <div className="day-section" key={shift}>
                    <h3>{shift} משמרת – תצוגת שבוע</h3>
                    <table className="schedule-grid">
                        <thead>
                            <tr>
                                <th>תפקיד</th>
                                {days.map(day => <th key={day}>{day}</th>)}
                            </tr>
                        </thead>
                        <tbody>
                            {positions.map(position => (
                                <tr key={position}>
                                    <td>{position}</td>
                                    {days.map(day => {
                                        const entries = (schedule.schedule[day][shift] || []).filter(e => e.position === position);
                                        const names = entries.map(entry => {
                                            const worker = idToWorker?.[String(entry.worker_id)];
                                            return worker?.name || `ID: ${entry.worker_id}`;
                                        }).join(', ');
                                        return (
                                            <td key={day} style={{ color: names.includes('ID:') ? 'red' : 'black' }}>
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

    if (isLoading) return <div className="loading-message">טוען סידורים...</div>;
    if (error) return <div className="error-message">{error}</div>;
    if (!hotelName && user) return <div className="error-message">למשתמש אין מקום עבודה משויך</div>;
    if (!user) return null;

    return (
        <div className="content-wrapper weekly-schedule-page">
            <h1>צפייה בסידורי עבודה - {hotelName}</h1>

            <div className="schedule-selection-controls" style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', marginBottom: 16 }}>
                <button
                    onClick={() => handleSelectSchedule("latest")}
                    style={selectedScheduleKey === "latest" ? activeButtonStyle : buttonStyle}
                    disabled={!schedules.latest}
                >
                    הצג סידור נוכחי
                    {schedules.latest?.relevantWeekStartDate && 
                        ` (${getWeekDateRangeStringForDisplay(schedules.latest.relevantWeekStartDate)})`}
                </button>

                {previousSchedules.length > 0 && <span style={{margin: "0 10px", fontWeight: 600}}>| הצג סידורים קודמים:</span>}
                {previousSchedules.map((prevSchedule, index) => (
                    <button
                        key={prevSchedule._id || index}
                        onClick={() => handleSelectSchedule(index)}
                        style={selectedScheduleKey === index ? activeButtonStyle : buttonStyle}
                    >
                        שבוע {index + 1} אחורה
                        {prevSchedule.relevantWeekStartDate && 
                            ` (${getWeekDateRangeStringForDisplay(prevSchedule.relevantWeekStartDate)})`}
                    </button>
                ))}

                {currentScheduleToDisplay && (
                    <button
                        onClick={() => setViewMode(prevMode => prevMode === "byDay" ? "wide" : "byDay")}
                        style={toggleButtonStyle}
                    >
                        {viewMode === "byDay" ? "🔄 הצג תצוגה שבועית רחבה" : "📅 הצג תצוגה יומית"}
                    </button>
                )}
            </div>

            {currentScheduleToDisplay?.schedule && (
                <div className="schedule-content">
                    <p style={{textAlign: 'center', fontSize: '0.9em', color: '#555'}}>
                        נוצר בתאריך: {new Date(currentScheduleToDisplay.generatedAt).toLocaleString('he-IL')}
                        {currentScheduleToDisplay.status === 'partial' && 
                            <span style={{color: 'orange', marginLeft: '10px'}}>(סידור חלקי)</span>}
                    </p>
                    {viewMode === "byDay" ? (
                        Object.entries(currentScheduleToDisplay.schedule).map(([day, shifts]) =>
                            renderDayTable(day, shifts)
                        )
                    ) : (
                        renderWideTable(currentScheduleToDisplay)
                    )}
                </div>
            )}
        </div>
    );
};

export default WeekleyScu;
