
document.getElementById("loginForm").addEventListener("submit", function (event) {
	event.preventDefault();

	// Fetch the input values
	var email = document.getElementById("email").value;
	var password = document.getElementById("password").value;

	// Perform your login logic here (e.g., send form data to server for validation)
	// For demonstration purposes, let's assume a simple validation

	if (email === "kolarony9@gmail.com.com" && password === "admin") {
		// Successful login
		alert("Login successful!");
		// Redirect the user to the dashboard or home page
		window.location.href = "/Login.html"; // Replace with the actual URL of your dashboard page
	} else {
		// Failed login
		alert("Invalid email or password. Please try again.");
	}
});
