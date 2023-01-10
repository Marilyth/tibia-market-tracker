var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
var __generator = (this && this.__generator) || function (thisArg, body) {
    var _ = { label: 0, sent: function() { if (t[0] & 1) throw t[1]; return t[1]; }, trys: [], ops: [] }, f, y, t, g;
    return g = { next: verb(0), "throw": verb(1), "return": verb(2) }, typeof Symbol === "function" && (g[Symbol.iterator] = function() { return this; }), g;
    function verb(n) { return function (v) { return step([n, v]); }; }
    function step(op) {
        if (f) throw new TypeError("Generator is already executing.");
        while (g && (g = 0, op[0] && (_ = 0)), _) try {
            if (f = 1, y && (t = op[0] & 2 ? y["return"] : op[0] ? y["throw"] || ((t = y["return"]) && t.call(y), 0) : y.next) && !(t = t.call(y, op[1])).done) return t;
            if (y = 0, t) op = [op[0] & 2, t.value];
            switch (op[0]) {
                case 0: case 1: t = op; break;
                case 4: _.label++; return { value: op[1], done: false };
                case 5: _.label++; y = op[1]; op = [0]; continue;
                case 7: op = _.ops.pop(); _.trys.pop(); continue;
                default:
                    if (!(t = _.trys, t = t.length > 0 && t[t.length - 1]) && (op[0] === 6 || op[0] === 2)) { _ = 0; continue; }
                    if (op[0] === 3 && (!t || (op[1] > t[0] && op[1] < t[3]))) { _.label = op[1]; break; }
                    if (op[0] === 6 && _.label < t[1]) { _.label = t[1]; t = op; break; }
                    if (t && _.label < t[2]) { _.label = t[2]; _.ops.push(op); break; }
                    if (t[2]) _.ops.pop();
                    _.trys.pop(); continue;
            }
            op = body.call(thisArg, _);
        } catch (e) { op = [6, e]; y = 0; } finally { f = t = 0; }
        if (op[0] & 5) throw op[1]; return { value: op[0] ? op[1] : void 0, done: true };
    }
};
/**
 * Fetches the list data from the API, according to the inputs, and fills the table with it.
 */
function fetchTable() {
    return __awaiter(this, void 0, void 0, function () {
        var table, i, name, minTraded, maxTraded, minSell, maxSell, minBuy, maxBuy, orderBy, orderDir, items;
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0: return [4 /*yield*/, setLoading(true)];
                case 1:
                    _a.sent();
                    hideError();
                    table = document.getElementById("item-table");
                    for (i = table.rows.length; i > 1; i--) {
                        table.deleteRow(i - 1);
                    }
                    return [4 /*yield*/, new Promise(function (resolve) { return setTimeout(resolve, 1000); })];
                case 2:
                    _a.sent();
                    name = document.getElementById("name-input").value;
                    minTraded = document.getElementById("name-input").value;
                    maxTraded = document.getElementById("name-input").value;
                    minSell = document.getElementById("name-input").value;
                    maxSell = document.getElementById("name-input").value;
                    minBuy = document.getElementById("name-input").value;
                    maxBuy = document.getElementById("name-input").value;
                    orderBy = document.getElementById("order-by").value;
                    orderDir = +document.getElementById("order-dir").value;
                    return [4 /*yield*/, getItems(name, minTraded, maxTraded, minSell, maxSell, minBuy, maxBuy, orderBy, orderDir)];
                case 3:
                    items = _a.sent();
                    items.forEach(function (item) {
                        var row = table.insertRow();
                        item.insertToRow(row);
                    });
                    return [4 /*yield*/, setLoading(false)];
                case 4:
                    _a.sent();
                    return [2 /*return*/];
            }
        });
    });
}
/**
 * Fetches the getItems endpoint of the API with the given options.
 * @param {string} name The name which the items must contain.
 * @param {number} minTraded The minimum amount of trades the items have per month.
 * @param {number} maxTraded The maximum amount of trades the items have per month.
 * @param {number} minSellPrice The minimum price the items sell for.
 * @param {number} maxSellPrice The maximum price the items sell for.
 * @param {number} minBuyPrice The minimum price the items are bought for.
 * @param {number} maxBuyPrice The maximum price the items are bought for.
 * @param {string} orderBy The value by which to order the list.
 * @param {number} orderDirection The direction, 1 or -1, by which to order the list.
 * @returns The list of items.
 */
function getItems(name, minTraded, maxTraded, minSellPrice, maxSellPrice, minBuyPrice, maxBuyPrice, orderBy, orderDirection) {
    return __awaiter(this, void 0, void 0, function () {
        var url, items, itemsList, error_1;
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0:
                    url = "http://127.0.0.1:5000/get_items?name=".concat(name, "&minTraded=").concat(minTraded) +
                        "&maxTraded=".concat(maxTraded, "&minSellPrice=").concat(minSellPrice, "&maxSellPrice=").concat(maxSellPrice) +
                        "&minBuyPrice=".concat(minBuyPrice, "&maxBuyPrice=").concat(maxBuyPrice, "&orderBy=").concat(orderBy, "&orderDirection=").concat(orderDirection);
                    _a.label = 1;
                case 1:
                    _a.trys.push([1, 3, , 4]);
                    return [4 /*yield*/, fetch(url).then(function (response) {
                            if (response.status != 200) {
                                setLoading(false);
                                showError(response.statusText);
                                throw new Error("Fetching items failed!");
                            }
                            return response.json();
                        })];
                case 2:
                    items = _a.sent();
                    itemsList = [];
                    items.forEach(function (item) {
                        itemsList.push(new MarketValues(item.SellPrice, item.BuyPrice, item.AvgSellPrice, item.AvgBuyPrice, item.Sold, item.Bought, item.RelProfit, item.PotProfit, item.Name));
                    });
                    return [2 /*return*/, itemsList];
                case 3:
                    error_1 = _a.sent();
                    setLoading(false);
                    showError(error_1.toString());
                    return [3 /*break*/, 4];
                case 4: return [2 /*return*/];
            }
        });
    });
}
/**
 * Fetches the getItemDetails endpoint of the API for the given item name.
 * @param {string} name The name of the item to retrieve details for.
 * @returns The details of the item.
 */
function getItemDetails(name) {
    return __awaiter(this, void 0, void 0, function () {
        var url, items;
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0:
                    url = "127.0.0.1/getItemDetails?name=".concat(name);
                    return [4 /*yield*/, fetch(url).then(function (response) {
                            if (response.status != 200) {
                                throw new Error("Fetching items failed!");
                            }
                            return response.json();
                        })];
                case 1:
                    items = _a.sent();
                    return [2 /*return*/, items];
            }
        });
    });
}
/**
 * Sets the page to appear loading, or reverts it.
 * @param isLoading
 */
function setLoading(isLoading) {
    return __awaiter(this, void 0, void 0, function () {
        var button, table, loadingRing;
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0:
                    button = document.getElementById("search-button");
                    table = document.getElementById("item-table");
                    loadingRing = document.getElementById("loading-ring");
                    if (isLoading) {
                        button.disabled = true;
                        table.style.opacity = "0";
                        loadingRing.style.opacity = "1";
                    }
                    else {
                        button.disabled = false;
                        table.style.opacity = "1";
                        loadingRing.style.opacity = "0";
                    }
                    // Wait for transitions to finish.
                    return [4 /*yield*/, new Promise(function (resolve) { return setTimeout(resolve, 150); })];
                case 1:
                    // Wait for transitions to finish.
                    _a.sent();
                    return [2 /*return*/];
            }
        });
    });
}
function showError(message) {
    var div = document.getElementById("error-message");
    div.innerText = message;
    div.style.display = "block";
}
function hideError() {
    var div = document.getElementById("error-message");
    div.innerText = "";
    div.style.display = "none";
}
var MarketValues = /** @class */ (function () {
    function MarketValues(sellOffer, buyOffer, monthSellOffer, monthBuyOffer, sold, bought, relativeProfit, potentialProfit, name) {
        this.sellOffer = sellOffer;
        this.buyOffer = buyOffer;
        this.monthBuyOffer = monthBuyOffer;
        this.monthSellOffer = monthSellOffer;
        this.sold = sold;
        this.bought = bought;
        this.name = name;
        this.potentialProfit = potentialProfit;
        this.relativeProfit = relativeProfit;
        this.traded = sold + bought;
        this.totalProfit = sellOffer - buyOffer;
    }
    MarketValues.prototype.insertToRow = function (row) {
        var name = row.insertCell();
        name.textContent = this.name;
        var sellOffer = row.insertCell();
        sellOffer.textContent = this.sellOffer.toString();
        var buyOffer = row.insertCell();
        buyOffer.textContent = this.buyOffer.toString();
        var traded = row.insertCell();
        traded.textContent = this.traded.toString();
        var totalProfit = row.insertCell();
        totalProfit.textContent = this.totalProfit.toString();
        var relativeProfit = row.insertCell();
        relativeProfit.textContent = "".concat(this.relativeProfit * 100, "%");
        var potentialProfit = row.insertCell();
        potentialProfit.textContent = this.potentialProfit.toString();
    };
    return MarketValues;
}());
//# sourceMappingURL=mainpage.js.map