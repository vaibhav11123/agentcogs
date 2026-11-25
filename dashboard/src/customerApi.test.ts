import assert from "node:assert/strict";
import { customerApiUrl } from "./customerApi";

assert.equal(customerApiUrl(undefined), "");
assert.equal(customerApiUrl(""), "");
assert.equal(customerApiUrl("   "), "");
assert.equal(customerApiUrl("not a url"), "");
assert.equal(customerApiUrl("https://agentcogs-api-production.up.railway.app"), "");
assert.equal(customerApiUrl("https://agentcogs-api-production.up.railway.app/"), "");
assert.equal(customerApiUrl("https://api.agentcogs.dev"), "");
assert.equal(customerApiUrl("https://api.customer.example"), "https://api.customer.example");
assert.equal(customerApiUrl("https://api.customer.example/"), "https://api.customer.example");
assert.equal(customerApiUrl("http://localhost:8000"), "http://localhost:8000");

console.log("customerApi: ok");
