import { createRequire } from 'node:module';

const require = createRequire(new URL('../apps/web/package.json', import.meta.url));
const { chromium } = require('@playwright/test');

const baseURL = process.env.LMS_AUDIT_BASE_URL ?? 'http://127.0.0.1:3000';
const password = process.env.LMS_AUDIT_DEMO_PASSWORD;
if (!password) throw new Error('LMS_AUDIT_DEMO_PASSWORD is required.');

const cases = [
  {
    email: 'owner@demo.local',
    landing: '/organizaciones/organizacion-demo/miembros',
    expected: ['Personas', 'Configuración institucional'],
    forbidden: ['Currículo', 'Cursos', 'Calendario', 'Evaluación y calificación'],
  },
  {
    email: 'administrator@demo.local',
    landing: '/organizaciones/organizacion-demo/aprendizaje/cohortes',
    expected: ['Currículo', 'Entregas y resultados', 'Grupos y matrículas'],
    forbidden: ['Autoría de evaluaciones', 'Calificación manual', 'Crear curso'],
  },
  {
    email: 'author@demo.local',
    landing: '/organizaciones/organizacion-demo/cursos',
    expected: ['Currículo', 'Crear curso', 'Autoría de evaluaciones'],
    forbidden: ['Mis grupos', 'Clases en vivo', 'Evaluación y calificación'],
  },
  {
    email: 'reviewer@demo.local',
    landing: '/organizaciones/organizacion-demo/cursos',
    expected: ['Currículo', 'Cursos', 'Autoría de evaluaciones'],
    forbidden: ['Crear curso', 'Mis grupos', 'Calificación manual'],
  },
  {
    email: 'instructor@demo.local',
    landing: '/organizaciones/organizacion-demo/aprendizaje/mis-asignaturas',
    expected: ['Mis asignaturas', 'Mis grupos', 'Evaluación y calificación'],
    forbidden: ['Currículo', 'Crear curso', 'Autoría de evaluaciones', 'Personas'],
  },
  {
    email: 'learner@demo.local',
    landing: '/organizaciones/organizacion-demo/aprendizaje',
    expected: ['Mi aprendizaje', 'Mi calendario', 'Mis evaluaciones'],
    forbidden: ['Resumen institucional', 'Cursos', 'Personas', 'Currículo'],
  },
];

const browser = await chromium.launch({ headless: true });
try {
  for (const item of cases) {
    const context = await browser.newContext({ viewport: { width: 390, height: 844 } });
    const page = await context.newPage();
    await page.goto(`${baseURL}/auth/iniciar-sesion`, { waitUntil: 'domcontentloaded' });
    await page.getByRole('textbox', { name: 'Correo electrónico' }).fill(item.email);
    await page.getByRole('textbox', { name: 'Contraseña' }).fill(password);
    await page.getByRole('button', { name: 'Iniciar sesión' }).click();
    await page.waitForURL((url) => !url.pathname.startsWith('/auth/'));
    if (new URL(page.url()).pathname !== item.landing) {
      throw new Error(`${item.email}: wrong landing ${page.url()}`);
    }
    const trigger = page.getByRole('button', { name: 'Mostrar u ocultar navegación' });
    await trigger.click();
    const sidebar = page.locator('[data-sidebar="sidebar"]').filter({ visible: true });
    await sidebar.first().waitFor({ state: 'visible' });
    const labels = (await sidebar.first().getByRole('link').allTextContents()).map((value) => value.trim());
    for (const expected of item.expected) {
      if (!labels.some((label) => label.includes(expected))) {
        throw new Error(`${item.email}: missing ${expected}`);
      }
    }
    for (const forbidden of item.forbidden) {
      if (labels.some((label) => label.includes(forbidden))) {
        throw new Error(`${item.email}: leaked ${forbidden}`);
      }
    }
    for (const redundant of ['Inicio', 'Mi perfil', 'Buscar', 'Resumen institucional']) {
      if (labels.some((label) => label === redundant)) {
        throw new Error(`${item.email}: redundant ${redundant}`);
      }
    }
    const width = await page.evaluate(() => ({
      clientWidth: document.documentElement.clientWidth,
      scrollWidth: document.documentElement.scrollWidth,
    }));
    if (width.scrollWidth > width.clientWidth) {
      throw new Error(`${item.email}: horizontal overflow ${width.scrollWidth}/${width.clientWidth}`);
    }
    console.log(`${item.email}: PASS ${width.clientWidth}px`);
    await context.close();
  }
} finally {
  await browser.close();
}
