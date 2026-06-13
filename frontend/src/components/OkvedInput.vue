<script setup lang="ts">
import { ref, computed } from 'vue'

const props = defineProps<{
  loading?: boolean
  error?: string
}>()

const emit = defineEmits<{
  suggest: [query: string]
}>()

const query = ref('')

const trimmedQuery = computed(() => query.value.trim())
const canSubmit = computed(() => trimmedQuery.value.length >= 2 && !props.loading)

function onSubmit() {
  if (!canSubmit.value) return
  emit('suggest', trimmedQuery.value)
}
</script>

<template>
  <div class="flex flex-col gap-3">
    <div class="flex gap-3">
      <input
        v-model="query"
        type="text"
        class="flex-1 bg-[#fcf8fa] border border-[#c6c6cd] rounded-lg py-3 px-4 text-base text-[#1b1b1d] focus:outline-none focus:ring-2 focus:ring-[#006a62] focus:border-transparent transition-shadow"
        placeholder="Введите ОКВЭД-код или описание деятельности"
        @keyup.enter="onSubmit"
      />
      <button
        class="bg-[#006a62] text-white text-sm font-medium px-5 py-3 rounded-lg hover:bg-[#005a54] transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-2 whitespace-nowrap"
        :disabled="!canSubmit"
        @click="onSubmit"
      >
        <span
          v-if="loading"
          class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"
        ></span>
        Подобрать категории
      </button>
    </div>
    <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
  </div>
</template>
