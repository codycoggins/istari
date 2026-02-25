import "@testing-library/jest-dom";

// JSDOM doesn't implement scrollIntoView; mock it globally so MessageList's
// auto-scroll useEffect doesn't throw in tests.
window.HTMLElement.prototype.scrollIntoView = () => {};
