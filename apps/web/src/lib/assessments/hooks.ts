'use client';

import { useMutation } from '@tanstack/react-query';

import {
  activateAssessmentDelivery,
  addAssessmentItem,
  addAssessmentSection,
  assignAssessmentCohort,
  assignAssessmentDelivery,
  createAssessment,
  createAssessmentDelivery,
  createAssessmentPool,
  createQuestion,
  createQuestionBank,
  createQuestionRevisionFromVersion,
  gradeAssessmentResponse,
  replaceAssessmentObjectives,
  replaceAssessmentPoolCandidates,
  reorderAssessmentItems,
  reorderAssessmentSections,
  saveAssessmentResponse,
  startAssessmentAttempt,
  submitAssessmentAttempt,
  transitionAssessmentRevision,
  transitionQuestionRevision,
  updateAssessmentRevision,
  updateAssessmentPool,
  updateAssessmentItem,
  updateQuestionBank,
  updateQuestionRevision,
  withdrawAssessmentDelivery,
} from './api';

export function useAssessmentMutation<TVariables, TResult>(
  operation: (variables: TVariables) => Promise<TResult>,
) {
  return useMutation({ mutationFn: operation, retry: false });
}

export {
  activateAssessmentDelivery,
  addAssessmentItem,
  addAssessmentSection,
  assignAssessmentCohort,
  assignAssessmentDelivery,
  createAssessment,
  createAssessmentDelivery,
  createAssessmentPool,
  createQuestion,
  createQuestionBank,
  createQuestionRevisionFromVersion,
  gradeAssessmentResponse,
  replaceAssessmentObjectives,
  replaceAssessmentPoolCandidates,
  reorderAssessmentItems,
  reorderAssessmentSections,
  saveAssessmentResponse,
  startAssessmentAttempt,
  submitAssessmentAttempt,
  transitionAssessmentRevision,
  transitionQuestionRevision,
  updateAssessmentRevision,
  updateAssessmentPool,
  updateAssessmentItem,
  updateQuestionBank,
  updateQuestionRevision,
  withdrawAssessmentDelivery,
};
