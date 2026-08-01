export const memberTypeOptions = [
  ['learner', 'Estudiante'],
  ['instructor', 'Docente'],
  ['guardian', 'Acudiente'],
  ['administrative', 'Personal administrativo'],
  ['support', 'Personal de apoyo'],
  ['other', 'Otro'],
] as const;

export const documentTypeOptions = [
  ['', 'Sin seleccionar'],
  ['RC', 'Registro civil'],
  ['TI', 'Tarjeta de identidad'],
  ['CC', 'Cédula de ciudadanía'],
  ['CE', 'Cédula de extranjería'],
  ['PPT', 'Permiso por protección temporal'],
  ['PA', 'Pasaporte'],
  ['DE', 'Documento extranjero'],
] as const;

export const genderOptions = [
  ['', 'Sin seleccionar'],
  ['female', 'Femenino'],
  ['male', 'Masculino'],
  ['non_binary', 'No binario'],
  ['other', 'Otro'],
  ['prefer_not_to_say', 'Prefiero no responder'],
] as const;

export const educationStageOptions = [
  ['', 'Sin seleccionar'],
  ['preschool', 'Preescolar'],
  ['school', 'Colegio'],
  ['technical', 'Institución técnica o tecnológica'],
  ['university', 'Universidad'],
  ['graduated', 'Graduado'],
  ['not_studying', 'Actualmente no estudia'],
  ['other', 'Otra'],
] as const;

export const educationLevelOptions = [
  ['', 'Sin seleccionar'],
  ['preschool', 'Preescolar'],
  ...Array.from(
    { length: 11 },
    (_, index) => [`grade_${index + 1}`, `${index + 1}.º`] as const,
  ),
  ['technical', 'Técnico profesional'],
  ['technologist', 'Tecnólogo'],
  ['undergraduate', 'Pregrado universitario'],
  ['specialization', 'Especialización'],
  ['masters', 'Maestría'],
  ['doctorate', 'Doctorado'],
  ['not_applicable', 'No aplica'],
] as const;

export const departmentOptions = [
  ['', 'Sin seleccionar'],
  ['05', 'Antioquia'],
  ['08', 'Atlántico'],
  ['11', 'Bogotá, D. C.'],
  ['13', 'Bolívar'],
  ['15', 'Boyacá'],
  ['17', 'Caldas'],
  ['18', 'Caquetá'],
  ['19', 'Cauca'],
  ['20', 'Cesar'],
  ['23', 'Córdoba'],
  ['25', 'Cundinamarca'],
  ['27', 'Chocó'],
  ['41', 'Huila'],
  ['44', 'La Guajira'],
  ['47', 'Magdalena'],
  ['50', 'Meta'],
  ['52', 'Nariño'],
  ['54', 'Norte de Santander'],
  ['63', 'Quindío'],
  ['66', 'Risaralda'],
  ['68', 'Santander'],
  ['70', 'Sucre'],
  ['73', 'Tolima'],
  ['76', 'Valle del Cauca'],
  ['81', 'Arauca'],
  ['85', 'Casanare'],
  ['86', 'Putumayo'],
  ['88', 'San Andrés, Providencia y Santa Catalina'],
  ['91', 'Amazonas'],
  ['94', 'Guainía'],
  ['95', 'Guaviare'],
  ['97', 'Vaupés'],
  ['99', 'Vichada'],
] as const;

export const socioeconomicStratumOptions = [
  ['not_reported', 'Prefiere no informar'],
  ['rural', 'Rural o sin estratificación'],
  ['1', 'Estrato 1'],
  ['2', 'Estrato 2'],
  ['3', 'Estrato 3'],
  ['4', 'Estrato 4'],
  ['5', 'Estrato 5'],
  ['6', 'Estrato 6'],
] as const;

export const registrationReasonOptions = [
  ['course', 'Tomar un curso'],
  ['school_support', 'Refuerzo escolar'],
  ['exam_preparation', 'Preparación para una evaluación'],
  ['professional_development', 'Formación profesional'],
  ['teaching', 'Enseñar o acompañar estudiantes'],
  ['institutional', 'Vinculación institucional'],
  ['other', 'Otro motivo'],
] as const;

export function ageFromBirthDate(value: string, today = new Date()) {
  if (!value) return null;
  const birth = new Date(`${value}T00:00:00`);
  if (Number.isNaN(birth.getTime()) || birth > today) return null;
  let age = today.getFullYear() - birth.getFullYear();
  if (
    today.getMonth() < birth.getMonth() ||
    (today.getMonth() === birth.getMonth() && today.getDate() < birth.getDate())
  )
    age -= 1;
  return age;
}

export function suggestedDocument(age: number | null) {
  if (age === null) return '';
  if (age < 7) return 'RC';
  if (age < 18) return 'TI';
  return 'CC';
}

export function educationInstitutionApplies(stage: string) {
  return ['preschool', 'school', 'technical', 'university'].includes(stage);
}
