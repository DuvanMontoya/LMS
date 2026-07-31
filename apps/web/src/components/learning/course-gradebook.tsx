import { Award, CheckCircle2, CircleDashed, ClipboardList } from 'lucide-react';

import type { GradebookStudentPayload } from '@/lib/assessments/server';

export function CourseGradebook({
  gradebooks,
}: Readonly<{ gradebooks: readonly GradebookStudentPayload[] }>) {
  if (!gradebooks.length) {
    return (
      <section className="course-tab-empty">
        <Award />
        <h2>Aún no hay un libro de calificaciones activo</h2>
        <p>
          Cuando la institución active el libro de este release, aquí aparecerán
          tus resultados ponderados.
        </p>
      </section>
    );
  }

  return (
    <div className="course-gradebook-list">
      {gradebooks.map((payload) => {
        const percent = payload.summary.weighted_percent_basis_points / 100;
        const complete = payload.summary.status === 'complete';
        return (
          <section className="course-gradebook" key={payload.gradebook.id}>
            <header>
              <div>
                <p className="academic-kicker">Release evaluado</p>
                <h2>{payload.gradebook.course_title}</h2>
                <p>
                  {payload.summary.completed_columns} de{' '}
                  {payload.summary.total_columns} actividades con resultado.
                </p>
              </div>
              <div
                aria-label={
                  complete
                    ? `Nota ponderada ${percent.toFixed(2)} por ciento`
                    : 'Nota ponderada provisional'
                }
                className="course-gradebook__score"
                data-complete={complete}
              >
                <span>{complete ? percent.toFixed(1) : '—'}</span>
                <small>{complete ? '%' : 'Provisional'}</small>
              </div>
            </header>
            <ul>
              {payload.gradebook.columns.map((column) => {
                const entry = payload.entries.find(
                  (candidate) => candidate.column_id === column.id,
                );
                const graded = entry?.status === 'graded';
                return (
                  <li key={column.id}>
                    <span className="course-gradebook__status">
                      {graded ? (
                        <CheckCircle2 aria-label="Calificada" />
                      ) : (
                        <CircleDashed aria-label="Pendiente" />
                      )}
                    </span>
                    <span className="course-gradebook__activity">
                      <strong>{column.title}</strong>
                      <small>
                        Peso {(column.weight_basis_points / 100).toFixed(2)} %
                      </small>
                    </span>
                    <span className="course-gradebook__result">
                      {entry?.percent_basis_points === null ||
                      entry?.percent_basis_points === undefined
                        ? 'Sin nota'
                        : `${(entry.percent_basis_points / 100).toFixed(2)} %`}
                    </span>
                  </li>
                );
              })}
            </ul>
            <footer>
              <ClipboardList />
              La calificación del libro y el progreso de lecciones son estados
              académicos independientes.
            </footer>
          </section>
        );
      })}
    </div>
  );
}
