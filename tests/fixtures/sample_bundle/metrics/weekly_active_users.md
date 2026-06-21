---
type: Metric
title: Weekly Active Users
description: Distinct users with at least one session in a 7-day window.
tags: [growth, engagement]
---
# Definition

COUNT(DISTINCT user_id) over a trailing 7-day window.
