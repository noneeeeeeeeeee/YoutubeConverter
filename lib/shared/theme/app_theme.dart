/// Material 3 Expressive theme for YouTube Converter
library;

import 'package:flutter/material.dart';

/// App theme configuration following Material 3 Expressive design
class AppTheme {
  // Default accent color (orange)
  static const Color defaultAccentColor = Color(0xFFF28C28);

  // Light theme colors
  static const Color lightBackground = Color(0xFFF7F8FA);
  static const Color lightSurface = Color(0xFFFFFFFF);
  static const Color lightSurfaceVariant = Color(0xFFF3F4F6);
  static const Color lightOnBackground = Color(0xFF212529);
  static const Color lightOnSurface = Color(0xFF212529);
  static const Color lightOnSurfaceVariant = Color(0xFF6B7280);
  static const Color lightOutline = Color(0xFFE5E7EB);
  static const Color lightOutlineVariant = Color(0xFFD6DBE1);

  // Dark theme colors
  static const Color darkBackground = Color(0xFF1C1D20);
  static const Color darkSurface = Color(0xFF202125);
  static const Color darkSurfaceVariant = Color(0xFF24252A);
  static const Color darkOnBackground = Color(0xFFF0F0F0);
  static const Color darkOnSurface = Color(0xFFF0F0F0);
  static const Color darkOnSurfaceVariant = Color(0xFFB0B2B8);
  static const Color darkOutline = Color(0xFF34353B);
  static const Color darkOutlineVariant = Color(0xFF40424A);

  // OLED theme colors (true black)
  static const Color oledBackground = Color(0xFF000000);
  static const Color oledSurface = Color(0xFF0A0A0A);
  static const Color oledSurfaceVariant = Color(0xFF111111);
  static const Color oledOnBackground = Color(0xFFF8F9FA);
  static const Color oledOnSurface = Color(0xFFF8F9FA);
  static const Color oledOnSurfaceVariant = Color(0xFFADB5BD);
  static const Color oledOutline = Color(0xFF212529);
  static const Color oledOutlineVariant = Color(0xFF2A2A2A);

  /// Create a ColorScheme from an accent color
  static ColorScheme _colorSchemeFromAccent(
      Color accent, bool isDark, bool isOled) {
    final brightness = isDark ? Brightness.dark : Brightness.light;

    return ColorScheme.fromSeed(
      seedColor: accent,
      brightness: brightness,
    ).copyWith(
      primary: accent,
      onPrimary: Colors.white,
      primaryContainer: _lightenColor(accent, 0.3),
      secondary: accent,
      onSecondary: Colors.white,
      secondaryContainer: _lightenColor(accent, 0.3),
      tertiary: accent,
      onTertiary: Colors.white,
      surface: isOled ? oledSurface : (isDark ? darkSurface : lightSurface),
      onSurface:
          isOled ? oledOnSurface : (isDark ? darkOnSurface : lightOnSurface),
      onSurfaceVariant: isOled
          ? oledOnSurfaceVariant
          : (isDark ? darkOnSurfaceVariant : lightOnSurfaceVariant),
      outline: isOled ? oledOutline : (isDark ? darkOutline : lightOutline),
      outlineVariant: isOled
          ? oledOutlineVariant
          : (isDark ? darkOutlineVariant : lightOutlineVariant),
    );
  }

  /// Lighten a color by a factor
  static Color _lightenColor(Color color, double factor) {
    final hsl = HSLColor.fromColor(color);
    final lightness = (hsl.lightness + factor).clamp(0.0, 1.0);
    return hsl.withLightness(lightness).toColor();
  }

  /// Darken a color by a factor
  static Color _darkenColor(Color color, double factor) {
    final hsl = HSLColor.fromColor(color);
    final lightness = (hsl.lightness - factor).clamp(0.0, 1.0);
    return hsl.withLightness(lightness).toColor();
  }

  /// Create light theme
  static ThemeData lightTheme({Color? accentColor}) {
    final accent = accentColor ?? defaultAccentColor;
    final colorScheme = _colorSchemeFromAccent(accent, false, false);

    return ThemeData(
      useMaterial3: true,
      colorScheme: colorScheme,
      brightness: Brightness.light,
      fontFamily: 'Roboto',

      // Scaffold
      scaffoldBackgroundColor: lightBackground,

      // App Bar
      appBarTheme: AppBarTheme(
        backgroundColor: lightBackground,
        foregroundColor: lightOnBackground,
        elevation: 0,
        scrolledUnderElevation: 1,
        surfaceTintColor: colorScheme.primary,
      ),

      // Navigation Rail
      navigationRailTheme: NavigationRailThemeData(
        backgroundColor: lightSurface,
        indicatorColor: colorScheme.primaryContainer,
        selectedIconTheme: IconThemeData(color: colorScheme.primary),
        unselectedIconTheme: IconThemeData(color: lightOnSurfaceVariant),
        selectedLabelTextStyle: TextStyle(
          color: colorScheme.primary,
          fontWeight: FontWeight.w600,
        ),
        unselectedLabelTextStyle: TextStyle(
          color: lightOnSurfaceVariant,
        ),
      ),

      // Cards
      cardTheme: CardTheme(
        color: lightSurface,
        surfaceTintColor: colorScheme.primary,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: BorderSide(color: lightOutline),
        ),
      ),

      // Elevated Button
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: colorScheme.primary,
          foregroundColor: Colors.white,
          elevation: 0,
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
        ),
      ),

      // Filled Button
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: colorScheme.primary,
          foregroundColor: Colors.white,
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
        ),
      ),

      // Outlined Button
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: colorScheme.primary,
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
          side: BorderSide(color: colorScheme.primary),
        ),
      ),

      // Text Button
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: colorScheme.primary,
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        ),
      ),

      // Input Decoration
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: lightSurface,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: lightOutlineVariant),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: lightOutlineVariant),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: colorScheme.primary, width: 2),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: colorScheme.error),
        ),
        contentPadding:
            const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      ),

      // Chip
      chipTheme: ChipThemeData(
        backgroundColor: lightSurfaceVariant,
        selectedColor: colorScheme.primaryContainer,
        labelStyle: TextStyle(color: lightOnSurface),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(8),
        ),
      ),

      // Progress Indicator
      progressIndicatorTheme: ProgressIndicatorThemeData(
        color: colorScheme.primary,
        linearTrackColor: colorScheme.primaryContainer,
      ),

      // Slider
      sliderTheme: SliderThemeData(
        activeTrackColor: colorScheme.primary,
        inactiveTrackColor: colorScheme.primaryContainer,
        thumbColor: colorScheme.primary,
        overlayColor: colorScheme.primary.withOpacity(0.12),
      ),

      // Switch
      switchTheme: SwitchThemeData(
        thumbColor: MaterialStateProperty.resolveWith((states) {
          if (states.contains(MaterialState.selected)) {
            return colorScheme.primary;
          }
          return null;
        }),
        trackColor: MaterialStateProperty.resolveWith((states) {
          if (states.contains(MaterialState.selected)) {
            return colorScheme.primaryContainer;
          }
          return null;
        }),
      ),

      // Checkbox
      checkboxTheme: CheckboxThemeData(
        fillColor: MaterialStateProperty.resolveWith((states) {
          if (states.contains(MaterialState.selected)) {
            return colorScheme.primary;
          }
          return Colors.transparent;
        }),
        checkColor: MaterialStateProperty.all(Colors.white),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(4),
        ),
      ),

      // Radio
      radioTheme: RadioThemeData(
        fillColor: MaterialStateProperty.resolveWith((states) {
          if (states.contains(MaterialState.selected)) {
            return colorScheme.primary;
          }
          return null;
        }),
      ),

      // Tab Bar
      tabBarTheme: TabBarTheme(
        labelColor: colorScheme.primary,
        unselectedLabelColor: lightOnSurfaceVariant,
        indicator: BoxDecoration(
          border: Border(
            bottom: BorderSide(color: colorScheme.primary, width: 2),
          ),
        ),
      ),

      // Divider
      dividerTheme: DividerThemeData(
        color: lightOutline,
        thickness: 1,
      ),

      // List Tile
      listTileTheme: ListTileThemeData(
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
        ),
      ),

      // Dialog
      dialogTheme: DialogTheme(
        backgroundColor: lightSurface,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
        ),
      ),

      // SnackBar
      snackBarTheme: SnackBarThemeData(
        backgroundColor: darkSurface,
        contentTextStyle: const TextStyle(color: darkOnSurface),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
        ),
        behavior: SnackBarBehavior.floating,
      ),

      // Scrollbar
      scrollbarTheme: ScrollbarThemeData(
        thumbColor:
            MaterialStateProperty.all(lightOnSurfaceVariant.withOpacity(0.5)),
        trackColor: MaterialStateProperty.all(lightSurfaceVariant),
        radius: const Radius.circular(8),
        thickness: MaterialStateProperty.all(8),
      ),
    );
  }

  /// Create dark theme
  static ThemeData darkTheme({Color? accentColor}) {
    final accent = accentColor ?? defaultAccentColor;
    final colorScheme = _colorSchemeFromAccent(accent, true, false);

    return ThemeData(
      useMaterial3: true,
      colorScheme: colorScheme,
      brightness: Brightness.dark,
      fontFamily: 'Roboto',
      scaffoldBackgroundColor: darkBackground,
      appBarTheme: AppBarTheme(
        backgroundColor: darkBackground,
        foregroundColor: darkOnBackground,
        elevation: 0,
        scrolledUnderElevation: 1,
        surfaceTintColor: colorScheme.primary,
      ),
      navigationRailTheme: NavigationRailThemeData(
        backgroundColor: darkSurface,
        indicatorColor: colorScheme.primaryContainer,
        selectedIconTheme: IconThemeData(color: colorScheme.primary),
        unselectedIconTheme: IconThemeData(color: darkOnSurfaceVariant),
        selectedLabelTextStyle: TextStyle(
          color: colorScheme.primary,
          fontWeight: FontWeight.w600,
        ),
        unselectedLabelTextStyle: TextStyle(
          color: darkOnSurfaceVariant,
        ),
      ),
      cardTheme: CardTheme(
        color: darkSurfaceVariant,
        surfaceTintColor: colorScheme.primary,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: BorderSide(color: darkOutline),
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: colorScheme.primary,
          foregroundColor: Colors.white,
          elevation: 0,
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: colorScheme.primary,
          foregroundColor: Colors.white,
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: colorScheme.primary,
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
          side: BorderSide(color: colorScheme.primary),
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: colorScheme.primary,
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: darkSurfaceVariant,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: darkOutlineVariant),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: darkOutlineVariant),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: colorScheme.primary, width: 2),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: colorScheme.error),
        ),
        contentPadding:
            const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      ),
      chipTheme: ChipThemeData(
        backgroundColor: darkSurfaceVariant,
        selectedColor: colorScheme.primaryContainer,
        labelStyle: TextStyle(color: darkOnSurface),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(8),
        ),
      ),
      progressIndicatorTheme: ProgressIndicatorThemeData(
        color: colorScheme.primary,
        linearTrackColor: colorScheme.primaryContainer,
      ),
      sliderTheme: SliderThemeData(
        activeTrackColor: colorScheme.primary,
        inactiveTrackColor: colorScheme.primaryContainer,
        thumbColor: colorScheme.primary,
        overlayColor: colorScheme.primary.withOpacity(0.12),
      ),
      switchTheme: SwitchThemeData(
        thumbColor: MaterialStateProperty.resolveWith((states) {
          if (states.contains(MaterialState.selected)) {
            return colorScheme.primary;
          }
          return null;
        }),
        trackColor: MaterialStateProperty.resolveWith((states) {
          if (states.contains(MaterialState.selected)) {
            return colorScheme.primaryContainer;
          }
          return null;
        }),
      ),
      checkboxTheme: CheckboxThemeData(
        fillColor: MaterialStateProperty.resolveWith((states) {
          if (states.contains(MaterialState.selected)) {
            return colorScheme.primary;
          }
          return Colors.transparent;
        }),
        checkColor: MaterialStateProperty.all(Colors.white),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(4),
        ),
      ),
      radioTheme: RadioThemeData(
        fillColor: MaterialStateProperty.resolveWith((states) {
          if (states.contains(MaterialState.selected)) {
            return colorScheme.primary;
          }
          return null;
        }),
      ),
      tabBarTheme: TabBarTheme(
        labelColor: colorScheme.primary,
        unselectedLabelColor: darkOnSurfaceVariant,
        indicator: BoxDecoration(
          border: Border(
            bottom: BorderSide(color: colorScheme.primary, width: 2),
          ),
        ),
      ),
      dividerTheme: DividerThemeData(
        color: darkOutline,
        thickness: 1,
      ),
      listTileTheme: ListTileThemeData(
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
        ),
      ),
      dialogTheme: DialogTheme(
        backgroundColor: darkSurface,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
        ),
      ),
      snackBarTheme: SnackBarThemeData(
        backgroundColor: darkSurfaceVariant,
        contentTextStyle: TextStyle(color: darkOnSurface),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
        ),
        behavior: SnackBarBehavior.floating,
      ),
      scrollbarTheme: ScrollbarThemeData(
        thumbColor:
            MaterialStateProperty.all(darkOnSurfaceVariant.withOpacity(0.5)),
        trackColor: MaterialStateProperty.all(darkSurfaceVariant),
        radius: const Radius.circular(8),
        thickness: MaterialStateProperty.all(8),
      ),
    );
  }

  /// Create OLED theme (true black)
  static ThemeData oledTheme({Color? accentColor}) {
    final accent = accentColor ?? defaultAccentColor;
    final colorScheme = _colorSchemeFromAccent(accent, true, true);

    return darkTheme(accentColor: accentColor).copyWith(
      scaffoldBackgroundColor: oledBackground,
      appBarTheme: AppBarTheme(
        backgroundColor: oledBackground,
        foregroundColor: oledOnBackground,
        elevation: 0,
      ),
      navigationRailTheme: NavigationRailThemeData(
        backgroundColor: oledSurface,
        indicatorColor: colorScheme.primaryContainer,
      ),
      cardTheme: CardTheme(
        color: oledSurfaceVariant,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: BorderSide(color: oledOutline),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: oledSurfaceVariant,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: oledOutlineVariant),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: oledOutlineVariant),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: colorScheme.primary, width: 2),
        ),
      ),
      dialogTheme: DialogTheme(
        backgroundColor: oledSurface,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
        ),
      ),
      snackBarTheme: SnackBarThemeData(
        backgroundColor: oledSurfaceVariant,
        contentTextStyle: TextStyle(color: oledOnSurface),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
        ),
        behavior: SnackBarBehavior.floating,
      ),
    );
  }

  /// Get theme by mode
  static ThemeData getTheme(String mode, {Color? accentColor}) {
    switch (mode.toLowerCase()) {
      case 'light':
        return lightTheme(accentColor: accentColor);
      case 'oled':
        return oledTheme(accentColor: accentColor);
      case 'dark':
      default:
        return darkTheme(accentColor: accentColor);
    }
  }
}
