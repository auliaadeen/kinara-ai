# Kinara AI — Data Model

## users/{uid}

{
  uid,
  email,
  role,
  createdAt
}

## users/{uid}/children/{childId}

{
  childId,
  name,
  educationalLevel,
  preferredLearningStyle,
  xp,
  streak,
  createdAt,
  updatedAt
}

## users/{uid}/children/{childId}/learningMemory/current

{
  masteryMap,
  weakConcepts,
  strongConcepts,
  recentTopics,
  recommendedDifficulty,
  learningTrend,
  totalXP,
  streak,
  lastSessionAt,
  updatedAt
}

## users/{uid}/children/{childId}/sessions/{sessionId}

{
  sessionId,
  topic,
  difficulty,
  questions,
  answerKey,
  answers,
  score,
  incorrectConcepts,
  timeSpentSeconds,
  completed,
  startedAt,
  completedAt
}

## users/{uid}/learningPaths/{pathId}

{
  pathId,
  targetGoal,
  durationDays,
  modules,
  progressPercentage,
  createdAt
}

## Design Rule

All user-owned documents must be scoped by Firebase UID.

Never query another user's documents.

Never trust client-provided UID.