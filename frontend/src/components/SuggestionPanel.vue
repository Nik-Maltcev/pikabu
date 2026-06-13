<script setup lang="ts">
import type { CategorySuggestion } from '../types/api'

const props = withDefaults(
  defineProps<{
    suggestions: CategorySuggestion[]
    message?: string
  }>(),
  {
    message: ''
  }
)

const emit = defineEmits<{
  acceptAll: []
  select: [suggestion: CategorySuggestion]
}>()
</script>

<template>
  <div class="flex flex-col gap-3">
    <!-- Suggestions list -->
    <template v-if="suggestions.length > 0">
      <div class="grid gap-3">
        <div
          v-for="suggestion in suggestions"
          :key="suggestion.topic_id"
          class="bg-[#fcf8fa] border border-[#c6c6cd] rounded-xl p-4 cursor-pointer hover:border-[#006a62] transition-colors"
          @click="emit('select', suggestion)"
        >
          <p class="text-[#1b1b1d] font-bold text-sm">{{ suggestion.name }}</p>
          <p class="text-[#45464d] text-xs mt-1">{{ suggestion.reason }}</p>
        </div>
      </div>
      <button
        class="bg-black text-white text-sm font-medium px-5 py-3 rounded-lg hover:bg-black/80 transition-colors w-full"
        @click="emit('acceptAll')"
      >
        Принять все
      </button>
    </template>

    <!-- Fallback message -->
    <template v-else>
      <p class="text-[#45464d] text-sm">
        {{ message || 'Не удалось подобрать категории' }}
      </p>
    </template>
  </div>
</template>
