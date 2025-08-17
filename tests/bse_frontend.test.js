/**
 * @jest-environment jsdom
 */

const { JSDOM } = require('jsdom');
const fs = require('fs');
const path = require('path');

const html = fs.readFileSync(path.resolve(__dirname, '../index.html'), 'utf8');

document.body.innerHTML = html;

// Mock the necessary functions and variables
let selected = { symbol: '500325', price: 2500 };
let portfolio = {};
const wsManager = {
    isConnected: true,
    send: jest.fn(),
};

// Load the script
const { placeOrder, setSelected, getPortfolio, clearPortfolio } = require('../bse_frontend.js');

describe('placeOrder', () => {
    beforeEach(() => {
        // Reset portfolio and selected stock before each test
        clearPortfolio();
        setSelected({ symbol: '500325', price: 2500 });
        document.body.innerHTML = html;
    });

    test('should add a new holding to the portfolio on buy', async () => {
        await placeOrder('buy', 2500, 10);
        const portfolio = getPortfolio();
        expect(portfolio['500325']).toEqual({ quantity: 10, avgPrice: 2500 });
    });

    test('should update an existing holding on buy', async () => {
        await placeOrder('buy', 2500, 10);
        await placeOrder('buy', 2600, 10);
        const portfolio = getPortfolio();
        expect(portfolio['500325'].quantity).toBe(20);
        expect(portfolio['500325'].avgPrice).toBe(2550);
    });

    test('should decrease the quantity of a holding on sell', async () => {
        await placeOrder('buy', 2550, 20);
        await placeOrder('sell', 2600, 5);
        const portfolio = getPortfolio();
        expect(portfolio['500325'].quantity).toBe(15);
    });

    test('should remove a holding if quantity becomes zero on sell', async () => {
        await placeOrder('buy', 2500, 10);
        await placeOrder('sell', 2600, 10);
        const portfolio = getPortfolio();
        expect(portfolio['500325']).toBeUndefined();
    });
});
