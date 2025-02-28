CREATE TABLE reports (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255),
    language VARCHAR(10),
    crime_type VARCHAR(50),
    details TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);