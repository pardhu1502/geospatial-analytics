import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import mapboxgl from 'mapbox-gl';
import MapboxDraw from '@mapbox/mapbox-gl-draw';
import apiClient from '../../api/client';
import 'mapbox-gl/dist/mapbox-gl.css';
import '@mapbox/mapbox-gl-draw/dist/mapbox-gl-draw.css';

const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN;

// Default view centered on the Western Ghats, India (see ARCHITECTURE.md seed data notes).
const DEFAULT_CENTER = [76.5, 11.5];
const DEFAULT_ZOOM = 8;

const SITE_TYPE_COLORS = {
  carbon: '#3b6e4f',
  biodiversity: '#c08a2e',
};

function siteColor(siteType) {
  return SITE_TYPE_COLORS[siteType] || '#2f5233';
}

function NewSiteForm({ onCancel, onSubmit, submitting, error }) {
  const [name, setName] = useState('');
  const [siteType, setSiteType] = useState('carbon');

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit({ name, siteType });
  };

  return (
    <div className="modal-backdrop" onClick={onCancel}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>Name this site</h2>
        {error && <div className="error-banner">{error}</div>}
        <form onSubmit={handleSubmit}>
          <div className="form-field">
            <label htmlFor="site-name">Site name</label>
            <input
              id="site-name"
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              autoFocus
            />
          </div>
          <div className="form-field">
            <label htmlFor="site-type">Site type</label>
            <select id="site-type" value={siteType} onChange={(e) => setSiteType(e.target.value)}>
              <option value="carbon">Carbon</option>
              <option value="biodiversity">Biodiversity</option>
            </select>
          </div>
          <div className="modal-actions">
            <button type="button" className="btn btn-secondary" onClick={onCancel}>
              Discard
            </button>
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? 'Saving...' : 'Save Site'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function ProjectMap() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const mapContainerRef = useRef(null);
  const mapRef = useRef(null);
  const drawRef = useRef(null);
  const styleLoadedRef = useRef(false);

  const [project, setProject] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');

  const [pendingGeometry, setPendingGeometry] = useState(null);
  const [savingSite, setSavingSite] = useState(false);
  const [saveError, setSaveError] = useState('');

  const renderSites = (sites) => {
    const map = mapRef.current;
    if (!map || !map.getSource('sites')) return;
    const features = (sites || [])
      .filter((s) => s.geom)
      .map((s) => ({
        type: 'Feature',
        geometry: s.geom,
        properties: {
          id: s.id,
          name: s.name,
          site_type: s.site_type,
          color: siteColor(s.site_type),
        },
      }));
    map.getSource('sites').setData({ type: 'FeatureCollection', features });

    if (features.length > 0) {
      const bounds = new mapboxgl.LngLatBounds();
      let hasCoords = false;
      features.forEach((f) => {
        const rings = f.geometry?.coordinates || [];
        rings.forEach((ring) => {
          ring.forEach((coord) => {
            bounds.extend(coord);
            hasCoords = true;
          });
        });
      });
      if (hasCoords) {
        map.fitBounds(bounds, { padding: 60, maxZoom: 14, duration: 0 });
      }
    }
  };

  // Load project data (project detail + nested sites).
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setLoadError('');
    apiClient
      .get(`/projects/${projectId}`)
      .then(({ data }) => {
        if (!cancelled) setProject(data);
      })
      .catch((err) => {
        if (!cancelled) {
          setLoadError(err.response?.data?.detail || 'Could not load project.');
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [projectId]);

  // Initialize the Mapbox map + Draw control once on mount.
  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return;

    mapboxgl.accessToken = MAPBOX_TOKEN;

    const map = new mapboxgl.Map({
      container: mapContainerRef.current,
      style: 'mapbox://styles/mapbox/satellite-streets-v12',
      center: DEFAULT_CENTER,
      zoom: DEFAULT_ZOOM,
    });
    mapRef.current = map;

    const draw = new MapboxDraw({
      displayControlsDefault: false,
      controls: { polygon: true, trash: true },
    });
    drawRef.current = draw;

    map.addControl(new mapboxgl.NavigationControl(), 'top-right');
    map.addControl(draw, 'top-left');

    map.on('load', () => {
      map.addSource('sites', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] },
      });
      map.addLayer({
        id: 'sites-fill',
        type: 'fill',
        source: 'sites',
        paint: {
          'fill-color': ['get', 'color'],
          'fill-opacity': 0.35,
        },
      });
      map.addLayer({
        id: 'sites-outline',
        type: 'line',
        source: 'sites',
        paint: {
          'line-color': ['get', 'color'],
          'line-width': 2,
        },
      });

      styleLoadedRef.current = true;
      renderSites(project?.sites);

      map.on('click', 'sites-fill', (e) => {
        const feature = e.features && e.features[0];
        if (feature) {
          navigate(`/projects/${projectId}/sites/${feature.properties.id}`);
        }
      });
      map.on('mouseenter', 'sites-fill', () => {
        map.getCanvas().style.cursor = 'pointer';
      });
      map.on('mouseleave', 'sites-fill', () => {
        map.getCanvas().style.cursor = '';
      });
    });

    map.on('draw.create', (e) => {
      const feature = e.features[0];
      setPendingGeometry(feature.geometry);
    });

    return () => {
      map.remove();
      mapRef.current = null;
      styleLoadedRef.current = false;
    };
  }, []);

  // Re-render site polygons whenever the project data changes.
  useEffect(() => {
    if (!project) return;
    if (styleLoadedRef.current) {
      renderSites(project.sites);
    }
  }, [project]);

  const cancelPendingSite = () => {
    setPendingGeometry(null);
    setSaveError('');
    if (drawRef.current) drawRef.current.deleteAll();
  };

  const handleSaveSite = async ({ name, siteType }) => {
    if (!pendingGeometry) return;
    setSavingSite(true);
    setSaveError('');
    try {
      const { data } = await apiClient.post(`/projects/${projectId}/sites`, {
        name,
        site_type: siteType,
        geom: pendingGeometry,
      });
      setProject((prev) => ({
        ...prev,
        sites: [...(prev?.sites || []), data],
      }));
      cancelPendingSite();
    } catch (err) {
      setSaveError(err.response?.data?.detail || 'Could not save site.');
    } finally {
      setSavingSite(false);
    }
  };

  return (
    <div className="map-page">
      <div className="map-toolbar">
        <div>
          <Link to="/" className="back-link">
            ← All Projects
          </Link>
          <h1>{project ? project.name : loading ? 'Loading project...' : 'Project'}</h1>
        </div>
      </div>

      {loadError && (
        <div className="page-container" style={{ paddingTop: '1rem', paddingBottom: 0 }}>
          <div className="error-banner">{loadError}</div>
        </div>
      )}

      <div className="map-container">
        <div ref={mapContainerRef} style={{ width: '100%', height: '100%' }} />
        <div className="map-hint">
          Use the polygon tool (top-left) to draw a new site boundary. Click an existing polygon to
          view its details.
        </div>
      </div>

      {pendingGeometry && (
        <NewSiteForm
          onCancel={cancelPendingSite}
          onSubmit={handleSaveSite}
          submitting={savingSite}
          error={saveError}
        />
      )}
    </div>
  );
}
