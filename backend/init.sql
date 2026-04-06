"""PostgreSQL initialization script with PostGIS extension."""

# Run this script after creating PostgreSQL database
# psql -U postgres -d aerocorridor -f init.sql

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- Enable PostGIS geometry functions
SELECT postgis_version();

-- Create indexes for spatial queries
CREATE INDEX idx_buildings_location ON buildings USING GIST(location);
CREATE INDEX idx_delivery_nodes_location ON delivery_nodes USING GIST(location);
CREATE INDEX idx_obstacles_base_loc ON obstacles USING GIST(base_location);
CREATE INDEX idx_risk_voxel_center ON risk_voxels USING GIST(center);

-- Create indexes for common queries
CREATE INDEX idx_buildings_city ON buildings(city);
CREATE INDEX idx_nodes_building_id ON delivery_nodes(building_id);
CREATE INDEX idx_orders_destination ON orders(destination_node_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_created_at ON orders(created_at DESC);
CREATE INDEX idx_telemetry_drone_id ON telemetry(drone_id);
CREATE INDEX idx_telemetry_created_at ON telemetry(created_at DESC);
CREATE INDEX idx_flight_logs_drone_id ON flight_logs(drone_id);
CREATE INDEX idx_risk_zone_color ON risk_voxels(zone_color);

-- Create functions for common spatial queries
CREATE OR REPLACE FUNCTION nearby_buildings(lat FLOAT, lon FLOAT, radius_km FLOAT DEFAULT 1.0)
RETURNS TABLE(building_id VARCHAR, name TEXT, distance_km FLOAT) AS $$
  SELECT 
    b.building_id,
    b.name,
    ST_DistanceSphere(b.location, ST_Point(lon, lat)) / 1000.0 as distance_km
  FROM buildings b
  WHERE ST_DWithin(b.location, ST_Point(lon, lat), radius_km * 1000)
  ORDER BY distance_km;
$$ LANGUAGE SQL;

CREATE OR REPLACE FUNCTION nearby_delivery_nodes(lat FLOAT, lon FLOAT, radius_km FLOAT DEFAULT 1.0)
RETURNS TABLE(node_id VARCHAR, node_name TEXT, altitude_msl FLOAT, distance_km FLOAT) AS $$
  SELECT 
    d.node_id,
    d.node_name,
    d.altitude_msl,
    ST_DistanceSphere(d.location, ST_Point(lon, lat)) / 1000.0 as distance_km
  FROM delivery_nodes d
  WHERE ST_DWithin(d.location, ST_Point(lon, lat), radius_km * 1000)
  ORDER BY distance_km;
$$ LANGUAGE SQL;

CREATE OR REPLACE FUNCTION risk_score_at_point(lat FLOAT, lon FLOAT, alt FLOAT)
RETURNS FLOAT AS $$
  SELECT COALESCE(AVG(r.composite_risk), 0.2)
  FROM risk_voxels r
  WHERE ST_DWithin(r.center, ST_Point(lon, lat, alt), 500);
$$ LANGUAGE SQL;

-- Vacuum analysis
VACUUM ANALYZE;
