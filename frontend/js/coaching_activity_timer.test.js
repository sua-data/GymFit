const test = require("node:test");
const assert = require("node:assert/strict");
const { CoachingActivityTimer } = require("./coaching_activity_timer.js");

function status(angle, count = 0, extras = {}) {
  return {
    person_detected: true,
    pose_valid: true,
    elbow_angle: angle,
    stage: angle >= 155 ? "UP" : angle <= 105 ? "DOWN" : null,
    count,
    ...extras,
  };
}

test("30 minutes idle after three repetitions is not counted", () => {
  const timer = new CoachingActivityTimer();
  let now = 0;
  timer.update(status(100), now);
  for (let count = 1; count <= 3; count += 1) {
    now += 1000;
    timer.update(status(165, count), now);
    now += 1000;
    timer.update(status(100, count), now);
  }
  for (let index = 0; index < 1800; index += 1) {
    now += 1000;
    timer.update(status(100, 3), now);
  }
  assert.ok(timer.getMilliseconds() < 20000);
  assert.equal(timer.getWholeMinutes(3), 0);
});

test("only moving intervals accumulate and movement can resume", () => {
  const timer = new CoachingActivityTimer();
  timer.update(status(100), 0);
  timer.update(status(115), 1000);
  timer.update(status(130), 2000);
  const beforeIdle = timer.getMilliseconds();
  timer.update(status(130), 3000);
  timer.update(status(130), 11000);
  const afterIdle = timer.getMilliseconds();
  timer.update(status(145), 12000);
  timer.update(status(160, 1), 13000);
  timer.update(status(145, 1), 14000);
  assert.ok(afterIdle >= beforeIdle);
  assert.ok(timer.getMilliseconds() > afterIdle);
});

test("pause, rest, missing person, and invalid pose are excluded", () => {
  const timer = new CoachingActivityTimer();
  timer.update(status(100), 0);
  timer.update(status(120), 1000);
  const active = timer.getMilliseconds();
  timer.suspend();
  timer.update(status(140), 31000, false);
  timer.resume();
  timer.update(status(140), 32000);
  timer.update(status(140, 0, { person_detected: false }), 33000);
  timer.update(status(140, 0, { pose_valid: false }), 34000);
  assert.equal(timer.getMilliseconds(), active);
});

test("zero repetitions and sub-minute activity follow zero-minute policy", () => {
  const timer = new CoachingActivityTimer();
  timer.activeMilliseconds = 59000;
  assert.equal(timer.getWholeMinutes(0), 0);
  assert.equal(timer.getWholeMinutes(3), 0);
  timer.activeMilliseconds = 60000;
  assert.equal(timer.getWholeMinutes(3), 1);
});

test("squat person_valid and average_angle fields are supported", () => {
  const timer = new CoachingActivityTimer();
  timer.update({ person_valid: true, pose_valid: true, average_angle: 120, stage: "UP", count: 0 }, 0);
  assert.equal(
    timer.update({ person_valid: true, pose_valid: true, average_angle: 105, stage: "DOWN", count: 0 }, 1000),
    true,
  );
});
