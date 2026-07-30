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
  createQuestion,
  createQuestionBank,
  gradeAssessmentResponse,
  replaceAssessmentObjectives,
  reorderAssessmentItems,
  reorderAssessmentSections,
  saveAssessmentResponse,
  startAssessmentAttempt,
  submitAssessmentAttempt,
  transitionAssessmentRevision,
  transitionQuestionRevision,
  updateAssessmentRevision,
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
  createQuestion,
  createQuestionBank,
  gradeAssessmentResponse,
  replaceAssessmentObjectives,
  reorderAssessmentItems,
  reorderAssessmentSections,
  saveAssessmentResponse,
  startAssessmentAttempt,
  submitAssessmentAttempt,
  transitionAssessmentRevision,
  transitionQuestionRevision,
  updateAssessmentRevision,
  updateAssessmentItem,
  updateQuestionBank,
  updateQuestionRevision,
  withdrawAssessmentDelivery,
};
