import type { Car, CarCreateInput } from '~/types/cars'
import type { ApiError } from '~/composables/useApi'

export const useCarStore = defineStore('car', () => {
    const cars = ref<Car[]>([])
    const isLoading = ref(false)
    const error = ref<string | null>(null)

    const { apiGet, apiPost, apiPatch, apiDelete } = useApi()

    const createCar = async (carInput: CarCreateInput): Promise<Car> => {
        isLoading.value = true
        error.value = null
        try {
            const createdCar = await apiPost<Car>('/cars', carInput)
            cars.value.push(createdCar)
            return createdCar
        } catch (e) {
            error.value = (e as ApiError).message
            throw e
        } finally {
            isLoading.value = false
        }
    }

    const fetchListCars = async () => {
        isLoading.value = true
        error.value = null
        try {
            cars.value = await apiGet<Car[]>('/cars')
        } catch (e) {
            error.value = (e as ApiError).message
            console.log(e)
        } finally {
            isLoading.value = false
        }
    }

    const fetchCarById = async (carId: number): Promise<Car> => {
        isLoading.value = true
        error.value = null
        try {
            const fetchedCar = await apiGet<Car>(`/cars/${carId}`)
            const existingIndex = cars.value.findIndex((car) => car.id === carId)
            if (existingIndex === -1) {
                cars.value.push(fetchedCar)
            } else {
                cars.value[existingIndex] = fetchedCar
            }
            return fetchedCar
        } catch (e) {
            error.value = (e as ApiError).message
            throw e
        } finally {
            isLoading.value = false
        }
    }

    const updateCar = async (carId: number, carInput: CarCreateInput): Promise<Car> => {
        isLoading.value = true
        error.value = null
        try {
            const updatedCar = await apiPatch<Car>(`/cars/${carId}`, carInput)
            cars.value = cars.value.map((car) => car.id === carId ? updatedCar : car)
            return updatedCar
        } catch (e) {
            error.value = (e as ApiError).message
            throw e
        } finally {
            isLoading.value = false
        }
    }

    const deleteCar = async (carId: number) => {
        isLoading.value = true
        error.value = null
        try {
            await apiDelete<void>(`/cars/${carId}`)
            cars.value = cars.value.filter((car) => car.id !== carId)
        } catch (e) {
            error.value = (e as ApiError).message
            console.log(e)
        } finally {
            isLoading.value = false
        }
    }

    return {
        cars,
        isLoading,
        error,
        fetchListCars,
        fetchCarById,
        createCar,
        updateCar,
        deleteCar
    }
})