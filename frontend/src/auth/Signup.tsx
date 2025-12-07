/*

AI-generated: 60% (Tool: ChatGPT, Cusor, primarily MUI component structure, form layout, error parsing and mapping,)
Human-written: 40% (logic: handleSignUp function, validation, integration with AuthContext, navigation after signup, state management)

Notes:

Most of the UI layout, styling, and basic form state setup were AI-assisted.

Human contributions handle the real signup flow: calling the registerUser endpoint, parsing errors, storing tokens, updating auth state, and redirecting on success.

*/
import { useEffect, useState } from "react";
import { Card, CardContent, Typography, TextField, Button, Box } from "@mui/material";
import { Link, useNavigate } from "react-router-dom"; 
import { registerUser } from "./endpoints/auth";
import { useAuth } from "./AuthContext";

interface FieldErrors {
  username?: string[];
  email?: string[];
  password?: string[];
  confirmPassword?: string[];
}

function SignUp() {
  const [username, setUserName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [errors, setErrors] = useState<FieldErrors>({});

  const { auth, login } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (auth.accessToken) {
      navigate("/home");
    }
  }, [auth.accessToken, navigate]);

  const isValid =
    username.trim() !== "" &&
    email.trim() !== "" &&
    password.trim() !== "" &&
    confirmPassword.trim() !== "" &&
    password === confirmPassword;

  const handleSignUp = async () => {
    const result = await registerUser({ username, email, password, confirmPassword });

    if (result.access && result.refresh) {
      login(result.access, result.refresh);
      navigate("/home");
    } else if (result.errors) {
      const fieldErrors: FieldErrors = {};
      result.errors.forEach(err => {
        const [field, message] = err.split(": ");
        if (field && message) {
          if (!fieldErrors[field as keyof FieldErrors]) {
            fieldErrors[field as keyof FieldErrors] = [];
          }
          fieldErrors[field as keyof FieldErrors]?.push(message);
        }
      });
      setErrors(fieldErrors);
    } else {
      setErrors({});
    }
  };

  return (
    <Box
      sx={{
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        bgcolor: "background.default",
      }}
    >
      <Card sx={{ width: 400, boxShadow: 6, borderRadius: 4 }}>
        <CardContent sx={{ p: 4 }}>
          <Typography variant="h4" color="primary" align="center" gutterBottom>
            Sign Up
          </Typography>

          {/* Username */}
          <TextField
            label="Username"
            fullWidth
            margin="normal"
            value={username}
            onChange={(e) => setUserName(e.target.value)}
            error={!!errors.username}
            helperText={errors.username?.join(" ")}
            slotProps={{ input: { style: { backgroundColor: "white" } } }}
          />

          {/* Email */}
          <TextField
            label="Email"
            type="email"
            fullWidth
            margin="normal"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            error={!!errors.email}
            helperText={errors.email?.join(" ")}
            slotProps={{ input: { style: { backgroundColor: "white" } } }}
          />

          {/* Password */}
          <TextField
            label="Password"
            type="password"
            fullWidth
            margin="normal"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            error={!!errors.password}
            helperText={errors.password?.join(" ")}
            slotProps={{ input: { style: { backgroundColor: "white" } } }}
          />

          {/* Confirm Password */}
          <TextField
            label="Confirm Password"
            type="password"
            fullWidth
            margin="normal"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            error={confirmPassword !== "" && password !== confirmPassword}
            helperText={
              confirmPassword !== "" && password !== confirmPassword
                ? "Passwords do not match"
                : errors.confirmPassword?.join(" ")
            }
            slotProps={{ input: { style: { backgroundColor: "white" } } }}
          />

          {/* Sign Up Button */}
          <Button
            variant="contained"
            color="primary"
            fullWidth
            sx={{ mt: 2 }}
            disabled={!isValid}
            onClick={handleSignUp}
          >
            Sign Up
          </Button>

          {/* Return to Login */}
          <Button
            component={Link}
            to="/login"
            variant="outlined"
            fullWidth
            sx={{ mt: 2, color: "black", borderColor: "black" }}
          >
            Return to Login
          </Button>
        </CardContent>
      </Card>
    </Box>
  );
}

export default SignUp;
