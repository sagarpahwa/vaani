import { StyleSheet, View } from 'react-native';

import {
  AUDIENCES,
  DURATIONS,
  OBJECTIVES,
  OCCASIONS,
  STYLES,
  type GoalForm,
} from '@/coaching/goal';
import { spacing } from '@/theme';

import { OptionGroup } from './OptionGroup';

interface GoalSignatureFormProps {
  value: GoalForm;
  onChange: (next: GoalForm) => void;
}

/** The Goal Signature editor shared by Mode A and Mode B. Each chip group edits
 *  one field of the form; selections re-weight the backend rubric because the
 *  option values embed the keywords in domain/goal_signature.py. */
export function GoalSignatureForm({ value, onChange }: GoalSignatureFormProps) {
  return (
    <View style={styles.form}>
      <OptionGroup
        label="Objective"
        options={OBJECTIVES}
        value={value.objective}
        onChange={(objective) => onChange({ ...value, objective })}
      />
      <OptionGroup
        label="Occasion"
        options={OCCASIONS}
        value={value.occasion}
        onChange={(occasion) => onChange({ ...value, occasion })}
      />
      <OptionGroup
        label="Audience"
        options={AUDIENCES}
        value={value.audience}
        onChange={(audience) => onChange({ ...value, audience })}
      />
      <OptionGroup
        label="Style"
        options={STYLES}
        value={value.style}
        onChange={(style) => onChange({ ...value, style })}
      />
      <OptionGroup
        label="Target length"
        options={DURATIONS}
        value={value.durationSeconds}
        onChange={(durationSeconds) => onChange({ ...value, durationSeconds })}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  form: { gap: spacing.md },
});
