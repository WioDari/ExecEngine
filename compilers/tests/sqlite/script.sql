SELECT 
    COALESCE(m.title, ts.title) AS content_title,
    COALESCE(m.original_title, ts.original_title) AS original_title,
    s.title AS season_title,
    vs.views,
    vs.view_rank,
    vs.start_date,
    vs.end_date,
    vs.duration,
    vs.cumulative_weeks_in_top10,
    vs.hours_viewed
FROM view_summary vs
LEFT JOIN movie m ON vs.movie_id = m.id
LEFT JOIN season s ON vs.season_id = s.id
LEFT JOIN tv_show ts ON s.tv_show_id = ts.id;