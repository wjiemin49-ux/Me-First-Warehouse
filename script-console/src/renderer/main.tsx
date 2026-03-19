import React from "react";
import ReactDOM from "react-dom/client";
import { HashRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "react-hot-toast";
import App from "./App";
import "./styles/index.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 2_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <HashRouter>
        <App />
      </HashRouter>
      <Toaster
        position="bottom-right"
        toastOptions={{
          style: {
            background: "rgba(9, 17, 28, 0.94)",
            color: "#f8fbff",
            border: "1px solid rgba(96, 165, 250, 0.25)",
          },
        }}
      />
    </QueryClientProvider>
  </React.StrictMode>,
);
