import "@testing-library/jest-dom";

// jsdom implements no layout, so Element.scrollIntoView is absent. Components
// that scroll a run into view would throw on every render under test; stubbing
// it here keeps that a test-environment concern rather than pushing optional
// chaining into the component, where it would hide a genuine failure.
if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = function scrollIntoView() {};
}

