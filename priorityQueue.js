const THRESHOLDS = {
  amber: 40,
  red: 70
};

class PriorityQueue {
  constructor() {
    this.heap = [];
  }

  insert(item) {
    this.heap.push(item);
    this.heap.sort((a, b) => b.score - a.score);
  }

  updateScore(victimId, newScore) {
    const index = this.heap.findIndex(item => item.victimId === victimId);
    if (index !== -1) {
      this.heap[index].score = newScore;
      this.heap.sort((a, b) => b.score - a.score);
    }
  }

  getTopN(n) {
    return this.heap.slice(0, n);
  }
}

function checkThresholdAndTrend(scores) {
  if (!scores || scores.length === 0) {
    return { latestScore: 0, riskLevel: "LOW", shouldAlert: false, trend: "STABLE" };
  }

  const latestScore = scores[scores.length - 1];
  let riskLevel = "LOW";
  let shouldAlert = false;

  if (latestScore >= THRESHOLDS.red) {
    riskLevel = "HIGH";
    shouldAlert = true;
  } else if (latestScore >= THRESHOLDS.amber) {
    riskLevel = "MEDIUM";
    shouldAlert = true;
  }

  let trend = "STABLE";
  if (scores.length >= 2) {
    const prevScore = scores[scores.length - 2];
    if (latestScore > prevScore) trend = "INCREASING";
    else if (latestScore < prevScore) trend = "DECREASING";
  }

  return { latestScore, riskLevel, shouldAlert, trend };
}

module.exports = {
  PriorityQueue,
  checkThresholdAndTrend,
  THRESHOLDS
};