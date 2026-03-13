import "@testing-library/jest-dom";

// JSDOM doesn't implement scrollIntoView; mock it globally so MessageList's
// auto-scroll useEffect doesn't throw in tests.
window.HTMLElement.prototype.scrollIntoView = () => {};

// JSDOM doesn't implement matchMedia; mock it so App's isNarrow state
// initialises without throwing.
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }),
});
