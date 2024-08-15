// Import required modules
const express = require("express");
const mysql = require("mysql2/promise");

// Create an Express.js app
const app = express();

// Middleware to parse form data
app.use(express.urlencoded({ extended: true }));

// Define database connection parameters
const dbConfig = {
	host: "localhost",
	user: "admin",
	password: "admin",
	database: "fyncakes",
};

// Define routes
app.get("/", (req, res) => {
	res.sendFile(__dirname + "/signup.html");
});

app.post("/signup", async (req, res) => {
	try {
		// Connect to the MySQL database
		const connection = await mysql.createConnection(dbConfig);

		// Extract user input from the request body
		const { username, email, password } = req.body;

		// Insert user signup details into the users table
		await connection.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)", [
			username,
			email,
			password,
		]);

		// Close the database connection
		await connection.end();

		// Redirect the user to a success page
		res.send("Signup successful!");
	} catch (error) {
		console.error("Error:", error);
		res.status(500).send("Internal Server Error");
	}
});

// Start the server
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
	console.log(`Server is running on port ${PORT}`);
});
