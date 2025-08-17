require('whatwg-fetch');
const { TextEncoder, TextDecoder } = require('util');

global.TextEncoder = TextEncoder;
global.TextDecoder = TextDecoder;

global.fetch = jest.fn((url) => {
  if (url.includes('/api/stocks')) {
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ data: { '500325': 'RELIANCE' } }),
    });
  }
  if (url.includes('/api/quote')) {
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ price: 2500, change: 10, pChange: 0.4 }),
    });
  }
  return Promise.resolve({
    ok: true,
    json: () => Promise.resolve({}),
  });
});