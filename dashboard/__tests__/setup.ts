import '@testing-library/jest-dom'

// Polyfill Element.scrollTo for jsdom (not implemented)
if (typeof Element.prototype.scrollTo !== 'function') {
  Element.prototype.scrollTo = function () {}
}
