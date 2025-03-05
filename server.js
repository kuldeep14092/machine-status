const express = require("express");
const mysql = require("mysql2");

const app = express();
const PORT = 3000;

// Set up EJS as the template engine
app.set("view engine", "ejs");

// Serve static files (CSS, JS, Images)
app.use(express.static("public"));

// Create MySQL database connection
const db = mysql.createConnection({
    host: "localhost",
    user: "root",
    password: "",
    database: "status",
});

// Connect to MySQL
db.connect((err) => {
    if (err) {
        console.error("Database connection failed: " + err.stack);
        return;
    }
    console.log("Connected to MySQL database.");
});

// Route to render the EJS page
app.get("/", (req, res) => {
    const query = "SELECT region_id, event_type, timestamp FROM blink_logs ORDER BY timestamp DESC";
    
    db.query(query, (err, results) => {
        if (err) {
            console.error("Error fetching data: " + err);
            res.status(500).send("Error fetching data");
            return;
        }
        res.render("index", { data: results });
    });
});

// API Route to get the latest data (used for polling)
app.get("/api/logs", (req, res) => {
    const query = "SELECT region_id, event_type, timestamp FROM blink_logs ORDER BY timestamp DESC";
    
    db.query(query, (err, results) => {
        if (err) {
            res.status(500).json({ error: "Error fetching data" });
            return;
        }
        res.json(results);
    });
});

// Start the server
app.listen(PORT, () => {
    console.log(`Server running at http://localhost:${PORT}`);
});
