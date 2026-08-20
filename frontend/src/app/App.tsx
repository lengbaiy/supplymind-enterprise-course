import { BrowserRouter } from "react-router-dom";
import { AppProviders } from "./AppProviders";
import { ErrorBoundary } from "./ErrorBoundary";
import { AppRoutes } from "./routes";

export function App() { return <ErrorBoundary><AppProviders><BrowserRouter><AppRoutes /></BrowserRouter></AppProviders></ErrorBoundary>; }
