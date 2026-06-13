<script setup lang="ts">
import type { Topic } from '../types/api'

const props = withDefaults(defineProps<{
  selectedTopics: Topic[]
  maxCount?: number
}>(), {
  maxCount: 5
})

const emit = defineEmits<{
  remove: [topicId: number]
}>()
</script>

<template>
  <div class="flex flex-col gap-3">
    <div class="flex items-center justify-between">
      <span class="text-sm text-[#45464d]">Выбрано: {{ props.selectedTopics.length }} / {{ props.maxCount }}</span>
    </div>
    <div class="flex flex-wrap gap-2">
      <span
        v-for="topic in props.selectedTopics"
        :key="topic.id"
        class="inline-flex items-center gap-1.5 px-3 py-1.5 bg-[#f0fdf9] border border-[#d1fae5] rounded-full text-sm text-[#006a62]"
      >
        {{ topic.name }}
        <button
          type="button"
          class="inline-flex items-center justify-center w-4 h-4 rounded-full hover:bg-[#d1fae5] transition-colors text-[#006a62]"
          @click="emit('remove', topic.id)"
          aria-label="Удалить"
        >
          <span class="text-xs leading-none">&times;</span>
        </button>
      </span>
    </div>
  </div>
</template>
