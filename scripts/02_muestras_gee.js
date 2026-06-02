/*
 * Rol 3 - Muestras etiquetadas via Google Earth Engine (Code Editor).
 *
 * Versión JS equivalente a 02_muestras_gee.py para correr en
 *   https://code.earthengine.google.com
 *
 * Pasos:
 *  1. Subir alcaldias_cdmx.geojson como FeatureCollection asset.
 *     (Assets -> NEW -> Shape files o Table upload)
 *  2. Reemplazar la variable ALC_ASSET de abajo con el ID del asset.
 *  3. Run. Al terminar, exporta el FeatureCollection a Drive como CSV.
 */

var ALC_ASSET = 'users/TU_USUARIO/alcaldias_cdmx';
var ANIO = 2024;
var FECHA_INI = ANIO + '-01-01';
var FECHA_FIN = ANIO + '-12-31';
var MUESTRAS_POR_CLASE = 1500;

var MAPEO_WC_KEYS   = [10, 30, 40, 50, 60, 80];
var MAPEO_WC_VALUES = [ 1,  2,  2,  3,  4,  5]; // bosque=1 pastizal=2 urbano=3 suelo=4 agua=5
var NOMBRES = ['__none__', 'bosque', 'pastizal', 'urbano', 'suelo_desnudo', 'agua'];

var alcaldias = ee.FeatureCollection(ALC_ASSET);
var aoi = alcaldias.geometry();

function mascaraNubesS2(img) {
  var scl = img.select('SCL');
  var mala = scl.eq(3).or(scl.eq(8)).or(scl.eq(9)).or(scl.eq(10));
  return img.updateMask(mala.not());
}

var s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
  .filterBounds(aoi)
  .filterDate(FECHA_INI, FECHA_FIN)
  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
  .map(mascaraNubesS2)
  .median()
  .select(['B02','B03','B04','B08','B11','B12']);

var ndvi = s2.normalizedDifference(['B08','B04']).rename('NDVI');
var ndwi = s2.normalizedDifference(['B03','B08']).rename('NDWI');
var features = s2.addBands([ndvi, ndwi]);

var wc = ee.Image('ESA/WorldCover/v100/2020').select('Map');
var claseId = wc.remap(MAPEO_WC_KEYS, MAPEO_WC_VALUES, 0).rename('clase_id');

var stack = features.addBands(claseId);

var muestras = stack.stratifiedSample({
  numPoints: MUESTRAS_POR_CLASE,
  classBand: 'clase_id',
  region: aoi,
  scale: 10,
  seed: 42,
  classValues: [1,2,3,4,5],
  classPoints: [MUESTRAS_POR_CLASE, MUESTRAS_POR_CLASE, MUESTRAS_POR_CLASE,
                MUESTRAS_POR_CLASE, MUESTRAS_POR_CLASE],
  geometries: true,
  dropNulls: true
});

muestras = muestras.map(function(f) {
  var cid = ee.Number(f.get('clase_id')).toInt();
  var clase = ee.List(NOMBRES).get(cid);
  var coord = f.geometry().coordinates();
  return f.set({
    clase: clase,
    lon: coord.get(0),
    lat: coord.get(1),
    fuente: 'worldcover'
  });
});

print('Total muestras:', muestras.size());
Map.centerObject(aoi, 9);
Map.addLayer(alcaldias.style({color: 'red', fillColor: '00000000'}), {}, 'Alcaldías');
Map.addLayer(muestras, {color: 'yellow'}, 'Muestras');

Export.table.toDrive({
  collection: muestras,
  description: 'rol3_muestras_gee',
  fileFormat: 'CSV',
  selectors: ['lon','lat','clase','fuente',
              'B02','B03','B04','B08','B11','B12','NDVI','NDWI']
});
