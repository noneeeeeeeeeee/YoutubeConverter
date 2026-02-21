/// Stepper widget for showing progress through steps
library;

import 'package:flutter/material.dart';

/// Stepper widget for showing progress through download steps
class StepperWidget extends StatelessWidget {
  final List<String> steps;
  final int currentStep;

  const StepperWidget({
    super.key,
    required this.steps,
    this.currentStep = 0,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          for (int i = 0; i < steps.length; i++) ...[
            _buildStep(context, i),
            if (i < steps.length - 1) _buildConnector(context, i),
          ],
        ],
      ),
    );
  }

  Widget _buildStep(BuildContext context, int index) {
    final isActive = index == currentStep;
    final isCompleted = index < currentStep;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      decoration: BoxDecoration(
        color: isActive
            ? Theme.of(context).colorScheme.primaryContainer
            : Colors.transparent,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: isActive || isCompleted
              ? Theme.of(context).colorScheme.primary
              : Theme.of(context).colorScheme.outline,
          width: isActive ? 2 : 1,
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (isCompleted)
            Icon(
              Icons.check_circle,
              size: 16,
              color: Theme.of(context).colorScheme.primary,
            )
          else
            Text(
              '${index + 1}',
              style: TextStyle(
                color: isActive
                    ? Theme.of(context).colorScheme.primary
                    : Theme.of(context).colorScheme.onSurfaceVariant,
                fontWeight: isActive ? FontWeight.w600 : FontWeight.normal,
                fontSize: 12,
              ),
            ),
          const SizedBox(width: 8),
          Text(
            steps[index],
            style: TextStyle(
              color: isActive
                  ? Theme.of(context).colorScheme.primary
                  : Theme.of(context).colorScheme.onSurfaceVariant,
              fontWeight: isActive ? FontWeight.w600 : FontWeight.normal,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildConnector(BuildContext context, int index) {
    final isCompleted = index < currentStep;

    return Container(
      width: 24,
      height: 2,
      margin: const EdgeInsets.symmetric(horizontal: 4),
      color: isCompleted
          ? Theme.of(context).colorScheme.primary
          : Theme.of(context).colorScheme.outline,
    );
  }
}
