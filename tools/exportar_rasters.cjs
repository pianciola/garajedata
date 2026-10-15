// node tools/exportar_rasters.cjs (requiere sharp; NODE_PATH puede indicar su carpeta).
const sharp = require('sharp');
const fs = require('node:fs/promises');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const img = path.join(root,'static/img');
const out = path.join(root,'exports/marca');
(async () => {
  const logo = await fs.readFile(path.join(img,'logo.svg'));
  const sello = await fs.readFile(path.join(img,'logo-sello.svg'));
  for (const [name,size] of [['logo-96.png',96],['logo-96.webp',96],['logo-sello-128.webp',128],['logo-icono.png',1024],['logo-sello.png',1024],['favicon.png',64],['app-192.png',192],['app-512.png',512]]) {
    const app = name.startsWith('app-');
    let source = name.includes('sello') || app ? sello : logo;
    if(app) source = Buffer.from(source.toString().replace('viewBox="0 0 256 256"','viewBox="-32 -32 320 320"').replace('width="256" height="256" rx="32"','x="-32" y="-32" width="320" height="320" rx="0"'));
    let image = sharp(source,{density:300}).resize(size,size);
    await image.toFile(path.join(img,name));
  }
  await sharp(logo,{density:1200}).resize(4096,4096).png().toFile(path.join(out,'garajedata-icono-original.png'));
  await sharp(path.join(img,'logo-completo.svg'),{density:1200}).resize({width:6000}).png().toFile(path.join(out,'garajedata-logo-completo-original.png'));
  await sharp(path.join(img,'logo-completo.svg'),{density:300}).resize({width:1800}).png().toFile(path.join(img,'logo-completo.png'));
  const full = await fs.readFile(path.join(img,'logo-completo.svg'));
  const data = full.toString('base64');
  const photo = (await fs.readFile(path.join(img,'muestra/ficha.webp'))).toString('base64');
  const social = Buffer.from(`<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630"><rect width="1200" height="630" fill="#0a0b0d"/><rect y="622" width="1200" height="8" fill="#e3262b"/><image href="data:image/svg+xml;base64,${data}" x="62" y="40" width="440" height="125"/><image href="data:image/webp;base64,${photo}" x="630" y="65" width="525" height="490" preserveAspectRatio="xMidYMid slice"/><text x="65" y="265" font-family="sans-serif" font-weight="bold" font-size="44" fill="#fff">La historia completa</text><text x="65" y="323" font-family="sans-serif" font-weight="bold" font-size="44" fill="#fff">de tu auto.</text><text x="65" y="390" font-family="sans-serif" font-size="24" fill="#adb5c0">Services, gastos y vencimientos.</text><text x="65" y="432" font-family="sans-serif" font-size="24" fill="#adb5c0">Todo en tu bitácora.</text><text x="65" y="535" font-family="sans-serif" font-size="20" fill="#adb5c0">Gratis · Sin email · Sin publicidad</text></svg>`);
  await sharp(social).jpeg({quality:95}).toFile(path.join(img,'og.jpg'));
  await sharp(social,{density:144}).png().toFile(path.join(out,'garajedata-social-original.png'));
  console.log('PNG 4096 px, logo completo 6000 px e iconos exportados desde SVG.');
})().catch(e=>{console.error(e);process.exit(1)});
