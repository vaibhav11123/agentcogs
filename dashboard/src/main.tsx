import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import App from "./App";
import { IconProvider } from "@/components/icons";
import { Toaster } from "@/components/ui/sonner";
import "./index.css";

const qc = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000, retry: 1 } },
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <IconProvider>
          <App />
          <Toaster position="top-right" />
        </IconProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>
);
