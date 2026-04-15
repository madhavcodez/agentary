"""Pool Concierge vertical.

Scores on-market single-family listings in a given ZIP code for "pool
readiness": how well a swimming pool fits the backyard after accounting
for setbacks, house footprint, and lot geometry.

Phase 1 Stream A components:
    * ``mission.run_pool_concierge_mission`` — end-to-end pipeline that
      pulls listings, enriches them with ATTOM / Regrid / Mapbox data,
      segments the backyard, places a candidate pool, and scores fit.
    * ``pool_placement.find_largest_pool_rectangle`` — heuristic
      rectangle search with 15° rotation improvement.
    * ``scoring.score_pool_fitness`` — deterministic fitness banding.

All heavy data providers are accessed through the connector layer in
``app.services.data_sources.connectors`` which already supports graceful
mock fallback when API keys are missing.
"""
