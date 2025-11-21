fn main() {
    let some_f32: Option<f32> = Some(1.3);
    let none_f32: Option<f32> = None;
    let some_i32: Option<i32> = Some(42);
    let none_i32: Option<i32> = None;
    let some_string: Option<String> = Some(String::from("hello"));
    let none_string: Option<String> = None;

    // Prevent optimization
    std::hint::black_box(&some_f32);
    std::hint::black_box(&none_f32);
    std::hint::black_box(&some_i32);
    std::hint::black_box(&none_i32);
    std::hint::black_box(&some_string);
    std::hint::black_box(&none_string);

    println!("some_f32: {:?}", some_f32);
    println!("none_f32: {:?}", none_f32);
    println!("some_i32: {:?}", some_i32);
    println!("none_i32: {:?}", none_i32);
    println!("some_string: {:?}", some_string);
    println!("none_string: {:?}", none_string);
}
