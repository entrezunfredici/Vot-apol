import js from '@eslint/js'
import tseslint from 'typescript-eslint'
import vue from 'eslint-plugin-vue'

export default [
  { ignores: ['dist/**', 'node_modules/**'] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  ...vue.configs['flat/recommended'].map((c) => ({ ...c, files: ['**/*.vue'] })),
  { files: ['**/*.vue'], languageOptions: { parserOptions: { parser: tseslint.parser } } },
  { rules: { 'vue/multi-word-component-names': 'off',
      'vue/singleline-html-element-content-newline': 'off' } },
]
