import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import App from "./App";
import "./index.css";

// This file is the browser entry point; application behavior remains in App.
// StrictMode keeps React's development-time checks around the component tree.
createRoot(document.getElementById("root")).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
