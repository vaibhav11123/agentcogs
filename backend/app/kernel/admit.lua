local spent_key, holds_key, exp_key = KEYS[1], KEYS[2], KEYS[3]
local run_id = ARGV[1]
local estimate = tonumber(ARGV[2])
local ttl = tonumber(ARGV[3])
local budget = tonumber(ARGV[4])
local now = tonumber(redis.call('TIME')[1])
local dead = redis.call('ZRANGEBYSCORE', exp_key, '-inf', now)
for _, id in ipairs(dead) do
  redis.call('HDEL', holds_key, id)
  redis.call('ZREM', exp_key, id)
end
local spent = tonumber(redis.call('GET', spent_key) or '0')
local held = 0
for _, v in ipairs(redis.call('HVALS', holds_key)) do
  held = held + tonumber(v)
end
local function decide(spent, held, estimate, budget)
  if budget < 0 then return 'ok' end
  if spent + held + estimate > budget then
    if spent + estimate > budget then return 'exceeded' end
    return 'busy'
  end
  if spent * 5 >= budget * 4 then return 'warn' end
  return 'ok'
end
local decision = decide(spent, held, estimate, budget)
if decision == 'exceeded' or decision == 'busy' then
  return {decision, spent, held}
end
redis.call('HSET', holds_key, run_id, estimate)
redis.call('ZADD', exp_key, now + ttl, run_id)
return {decision, spent, held}
-- SETTLE
local spent_key, holds_key, exp_key, settled_key = KEYS[1], KEYS[2], KEYS[3], KEYS[4]
local actual = tonumber(ARGV[1])
local run_id = ARGV[2]
if redis.call('SET', settled_key, '1', 'NX') == false then
  return 0
end
redis.call('HDEL', holds_key, run_id)
redis.call('ZREM', exp_key, run_id)
redis.call('INCRBY', spent_key, actual)
return 1
-- SWEEP
local holds_key, exp_key = KEYS[1], KEYS[2]
local now = tonumber(redis.call('TIME')[1])
local dead = redis.call('ZRANGEBYSCORE', exp_key, '-inf', now)
for _, id in ipairs(dead) do
  redis.call('HDEL', holds_key, id)
  redis.call('ZREM', exp_key, id)
end
return #dead
